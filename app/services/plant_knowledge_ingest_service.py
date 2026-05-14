"""PlantKnowledgeIngestService — TICKET-014A.

Loads an Excel workbook and upserts rows into the 7 knowledge tables.
Idempotency: rows whose source_row_hash hasn't changed are skipped.

No LLM, no vector index.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.plant_knowledge import IngestSummary
from app.models.plant_care_requirement import PlantCareRequirement
from app.models.plant_knowledge_entry import PlantKnowledgeEntry
from app.models.plant_knowledge_source import PlantKnowledgeSource
from app.models.plant_pest_reference import PlantPestReference
from app.models.plant_placement import PlantPlacement
from app.models.plant_seasonal_watering import PlantSeasonalWatering
from app.models.plant_visual_trait import PlantVisualTrait

# ---------------------------------------------------------------------------
# Excel column map — keys are our field names, values are possible Korean headers.
# The loader picks the first header that exists in the workbook.
# ---------------------------------------------------------------------------

COLUMN_MAP: dict[str, list[str]] = {
    "nongsaro_id": ["농사로ID", "고유번호", "ID", "id"],
    "korean_name": ["한국명", "식물명", "국명"],
    "scientific_name": ["학명", "Scientific Name"],
    "common_name": ["영문명", "영명", "Common Name"],
    "family": ["과명", "과"],
    "origin": ["원산지"],
    "growth_temp_text": ["생육온도", "재배온도", "적정온도"],
    "light_requirement": ["광요구도", "광도", "빛 요구도"],
    "watering_frequency": ["물주기", "관수주기", "관수"],
    "soil_type": ["토양", "배양토"],
    "fertilizer_info": ["비료", "시비"],
    "spring_watering": ["물주기_봄", "봄 물주기", "봄물주기", "봄"],
    "summer_watering": ["물주기_여름", "여름 물주기", "여름물주기", "여름"],
    "autumn_watering": ["물주기_가을", "가을 물주기", "가을물주기", "가을"],
    "winter_watering": ["물주기_겨울", "겨울 물주기", "겨울물주기", "겨울"],
    "pest_text": ["병충해", "충해"],
    "disease_text": ["병충해관리", "질병", "병해"],
    "leaf_color": ["잎색", "잎 색상", "엽색"],
    "leaf_shape": ["잎형태", "잎 형태", "엽형"],
    "flower_color": ["꽃색", "꽃 색상", "화색"],
    "flower_season": ["꽃피는계절", "개화기", "개화 시기", "꽃 시기"],
    "height_text": ["성장높이(cm)", "초장", "높이", "식물 높이"],
    "placement_locations": ["배치장소", "배치 장소", "재배 환경", "실내외"],
    "is_toxic_raw": ["독성", "독성 유무", "독성여부"],
    "toxicity_detail": ["독성 설명", "독성 상세"],
    "fragrance": ["냄새", "향기"],
}

_PEST_SPLIT_RE = re.compile(r"[,、\n·및]+")


def _str(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def _bool_from_text(v: Any) -> bool | None:
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in ("유", "있음", "yes", "true", "1", "o", "독성있음"):
        return True
    if s in ("무", "없음", "no", "false", "0", "x", "독성없음"):
        return False
    return None


def _parse_pest_terms(text: str | None) -> list[str]:
    if not text:
        return []
    return [t.strip() for t in _PEST_SPLIT_RE.split(text) if t.strip()]


def _row_hash(raw_values: list[Any]) -> str:
    joined = "|".join("" if v is None else str(v) for v in raw_values)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _build_col_index(headers: list[str]) -> dict[str, int]:
    """Map each logical field to the column index of its first matching header."""
    header_lower = {h.strip().lower(): i for i, h in enumerate(headers)}
    index: dict[str, int] = {}
    for field, candidates in COLUMN_MAP.items():
        for candidate in candidates:
            if candidate.strip().lower() in header_lower:
                index[field] = header_lower[candidate.strip().lower()]
                break
    return index


def _get(row: tuple[Any, ...], col_index: dict[str, int], field: str) -> Any:
    idx = col_index.get(field)
    return row[idx] if idx is not None else None


class PlantKnowledgeIngestService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---------------------------------------------------------------------- public

    async def ingest_file(self, file_path: str | Path) -> IngestSummary:
        from app.ingestion.excel_loader import load_workbook_rows

        path = Path(file_path)
        summary = IngestSummary(source_file=str(path))

        headers, data_rows = load_workbook_rows(path)
        if not headers:
            return summary

        col_index = _build_col_index(headers)
        summary.total_rows = len(data_rows)

        for row_num, raw_row in enumerate(data_rows, start=2):
            try:
                status = await self._process_row(
                    raw_row=raw_row,
                    col_index=col_index,
                    row_number=row_num,
                    source_file=path.name,
                )
                if status == "inserted":
                    summary.inserted += 1
                elif status == "updated":
                    summary.updated += 1
                else:
                    summary.ignored += 1
            except Exception as exc:  # noqa: BLE001
                summary.errors += 1
                summary.error_details.append(f"row {row_num}: {exc}")

        return summary

    # ---------------------------------------------------------------------- private

    async def _process_row(
        self,
        raw_row: tuple[Any, ...],
        col_index: dict[str, int],
        row_number: int,
        source_file: str,
    ) -> str:
        nongsaro_id = _str(_get(raw_row, col_index, "nongsaro_id"))
        if not nongsaro_id:
            raise ValueError("nongsaro_id is missing")

        scientific_name = _str(_get(raw_row, col_index, "scientific_name"))
        if not scientific_name:
            raise ValueError("scientific_name is required")

        korean_name = _str(_get(raw_row, col_index, "korean_name")) or nongsaro_id
        row_hash = _row_hash(list(raw_row))
        now = datetime.now(UTC)

        # ---- idempotency check ------------------------------------------
        existing_entry = await self._find_entry(nongsaro_id)

        if existing_entry is not None:
            latest_src = await self._find_latest_source(existing_entry.id)
            if latest_src is not None and latest_src.source_row_hash == row_hash:
                return "ignored"
            # Hash changed → update child tables
            await self._update_children(existing_entry, raw_row, col_index, now)
            existing_entry.korean_name = korean_name
            existing_entry.scientific_name = scientific_name
            existing_entry.common_name = _str(_get(raw_row, col_index, "common_name"))
            existing_entry.family = _str(_get(raw_row, col_index, "family"))
            existing_entry.origin = _str(_get(raw_row, col_index, "origin"))
            existing_entry.updated_at = now
            await self._add_source(existing_entry.id, source_file, row_number, nongsaro_id, row_hash, "updated", now)
            return "updated"

        # ---- new entry ---------------------------------------------------
        entry = PlantKnowledgeEntry(
            id=uuid.uuid4(),
            nongsaro_id=nongsaro_id,
            korean_name=korean_name,
            scientific_name=scientific_name,
            common_name=_str(_get(raw_row, col_index, "common_name")),
            family=_str(_get(raw_row, col_index, "family")),
            origin=_str(_get(raw_row, col_index, "origin")),
            created_at=now,
            updated_at=now,
        )
        self.session.add(entry)
        await self.session.flush()

        await self._insert_children(entry.id, raw_row, col_index, now)
        await self._add_source(entry.id, source_file, row_number, nongsaro_id, row_hash, "inserted", now)
        return "inserted"

    async def _find_entry(self, nongsaro_id: str) -> PlantKnowledgeEntry | None:
        result = await self.session.execute(
            select(PlantKnowledgeEntry).where(PlantKnowledgeEntry.nongsaro_id == nongsaro_id)
        )
        return result.scalar_one_or_none()

    async def _find_latest_source(self, entry_id: uuid.UUID) -> PlantKnowledgeSource | None:
        result = await self.session.execute(
            select(PlantKnowledgeSource)
            .where(PlantKnowledgeSource.entry_id == entry_id)
            .order_by(PlantKnowledgeSource.ingested_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _insert_children(
        self,
        entry_id: uuid.UUID,
        raw_row: tuple[Any, ...],
        col_index: dict[str, int],
        now: datetime,
    ) -> None:
        g = lambda f: _get(raw_row, col_index, f)  # noqa: E731

        self.session.add(
            PlantCareRequirement(
                id=uuid.uuid4(),
                entry_id=entry_id,
                growth_temp_text=_str(g("growth_temp_text")),
                light_requirement=_str(g("light_requirement")),
                watering_frequency=_str(g("watering_frequency")),
                soil_type=_str(g("soil_type")),
                fertilizer_info=_str(g("fertilizer_info")),
                created_at=now,
                updated_at=now,
            )
        )
        self.session.add(
            PlantSeasonalWatering(
                id=uuid.uuid4(),
                entry_id=entry_id,
                spring=_str(g("spring_watering")),
                summer=_str(g("summer_watering")),
                autumn=_str(g("autumn_watering")),
                winter=_str(g("winter_watering")),
                created_at=now,
                updated_at=now,
            )
        )
        pest_text = _str(g("pest_text"))
        disease_text = _str(g("disease_text"))
        self.session.add(
            PlantPestReference(
                id=uuid.uuid4(),
                entry_id=entry_id,
                pest_text=pest_text,
                disease_text=disease_text,
                parsed_pest_terms=_parse_pest_terms(
                    (pest_text or "") + ("," if pest_text and disease_text else "") + (disease_text or "")
                ),
                created_at=now,
                updated_at=now,
            )
        )
        self.session.add(
            PlantVisualTrait(
                id=uuid.uuid4(),
                entry_id=entry_id,
                leaf_color=_str(g("leaf_color")),
                leaf_shape=_str(g("leaf_shape")),
                flower_color=_str(g("flower_color")),
                flower_season=_str(g("flower_season")),
                height_text=_str(g("height_text")),
                created_at=now,
                updated_at=now,
            )
        )
        self.session.add(
            PlantPlacement(
                id=uuid.uuid4(),
                entry_id=entry_id,
                placement_locations=_str(g("placement_locations")),
                is_toxic=_bool_from_text(g("is_toxic_raw")),
                toxicity_detail=_str(g("toxicity_detail")),
                fragrance=_str(g("fragrance")),
                created_at=now,
                updated_at=now,
            )
        )
        await self.session.flush()

    async def _update_children(
        self,
        entry: PlantKnowledgeEntry,
        raw_row: tuple[Any, ...],
        col_index: dict[str, int],
        now: datetime,
    ) -> None:
        # Delete existing child rows; re-insert fresh ones.
        for model in (
            PlantCareRequirement,
            PlantSeasonalWatering,
            PlantPestReference,
            PlantVisualTrait,
            PlantPlacement,
        ):
            result = await self.session.execute(
                select(model).where(model.entry_id == entry.id)  # type: ignore[attr-defined]
            )
            for row in result.scalars().all():
                await self.session.delete(row)
        await self.session.flush()
        await self._insert_children(entry.id, raw_row, col_index, now)

    async def _add_source(
        self,
        entry_id: uuid.UUID,
        source_file: str,
        row_number: int,
        nongsaro_id: str,
        row_hash: str,
        status: str,
        now: datetime,
    ) -> None:
        self.session.add(
            PlantKnowledgeSource(
                id=uuid.uuid4(),
                entry_id=entry_id,
                source_file=source_file,
                source_row_number=row_number,
                nongsaro_id=nongsaro_id,
                source_row_hash=row_hash,
                ingest_status=status,
                ingested_at=now,
            )
        )
        await self.session.flush()
