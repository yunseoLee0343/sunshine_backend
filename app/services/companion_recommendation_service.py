"""CompanionRecommendationService — TICKET-021.

Loads candidates from species_profiles, reads the plant's latest environment
snapshot, delegates scoring to filter_companions (TICKET-020), and returns
only compatible results.

Also exports:
  - PlantOwnershipError  — raised when user_id does not match plant.user_id
  - format_companion_answer — pure function → ParsedAnswer for chat integration
"""

from __future__ import annotations

import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.companion import CompanionCandidate, RoomEnvironment
from app.models.environment_snapshot import EnvironmentSnapshot
from app.models.plant import Plant
from app.models.species_profile import SpeciesProfile
from app.schemas.chat_answer import ParsedAnswer
from app.schemas.companion_recommendation import (
    CompanionRecommendationItem,
    CompanionRecommendationResponse,
)
from app.services.companion_filter_service import filter_companions
from app.services.evidence_builder import PlantNotFoundError


class PlantOwnershipError(Exception):
    """Raised when the requesting user does not own the plant."""


# ---------------------------------------------------------------------------
# Text formatter (pure — no I/O)
# ---------------------------------------------------------------------------


def format_companion_answer(resp: CompanionRecommendationResponse | None) -> ParsedAnswer:
    """Convert a CompanionRecommendationResponse into [결론][근거][행동][주의]."""
    if resp is None or not resp.recommendations:
        return ParsedAnswer(
            결론="현재 환경에 적합한 동반 식물을 찾지 못했습니다.",
            근거=(
                "환경 스냅샷이 없거나 호환 가능한 식물 종이 데이터베이스에 없습니다. "
                "센서 데이터를 수집한 후 다시 시도해 주세요."
            ),
            행동="환경 데이터(조도·습도·온도)를 수집하거나 전문가에게 문의하세요.",
            주의="추가 환경 정보가 확보된 후 재조회를 권장합니다.",
        )

    recs = resp.recommendations
    top = recs[0]
    count = len(recs)

    # [결론]
    결론 = (
        f"{count}가지 동반 식물을 추천합니다. "
        f"최고 호환 식물은 '{top.common_name}'"
        f"(호환 점수: {top.compatibility_score:.2f})입니다."
    )

    # [근거]
    근거_lines = [
        f"현재 환경 데이터 기반 분석 "
        f"({'스냅샷 있음' if resp.environment_available else '스냅샷 없음'}) 결과:"
    ]
    for i, rec in enumerate(recs[:3], 1):
        reasons_short = "; ".join(rec.match_reasons[:2]) if rec.match_reasons else "조건 충족"
        근거_lines.append(f"{i}. {rec.common_name} (점수: {rec.compatibility_score:.2f}) — {reasons_short}")
    근거 = "\n".join(근거_lines)

    # [행동]
    행동_lines = ["추천 동반 식물 목록 (호환 점수 내림차순):"]
    for i, rec in enumerate(recs, 1):
        sci = f" / {rec.scientific_name}" if rec.scientific_name else ""
        행동_lines.append(f"{i}. {rec.common_name}{sci} | 점수: {rec.compatibility_score:.2f}")
    행동 = "\n".join(행동_lines)

    # [주의]
    all_cautions: list[str] = list(
        dict.fromkeys(
            note
            for rec in recs
            for note in rec.caution_notes
        )
    )
    if all_cautions:
        주의 = "일부 추천 식물 주의 사항: " + "; ".join(all_cautions)
    else:
        주의 = (
            "현재 안전 경고 사항이 없습니다. "
            "새 식물 도입 후 기존 식물 상태를 모니터링하세요."
        )

    return ParsedAnswer(결론=결론, 근거=근거, 행동=행동, 주의=주의)


def companion_prompt_hash(plant_id: uuid.UUID, question: str) -> str:
    """Deterministic hash for companion answers (no actual prompt used)."""
    raw = f"companion:{plant_id}:{question}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class CompanionRecommendationService:
    """Loads candidates and environment from DB, delegates to filter_companions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def recommend(
        self,
        plant_id: uuid.UUID,
        user_id: uuid.UUID,
        top_k: int = 5,
    ) -> CompanionRecommendationResponse:
        # ---- 1. plant + ownership ----------------------------------------
        plant = await self.session.get(Plant, plant_id)
        if plant is None:
            raise PlantNotFoundError(f"plant {plant_id} not found")
        if plant.user_id != user_id:
            raise PlantOwnershipError(
                f"plant {plant_id} is not owned by user {user_id}"
            )

        # ---- 2. current room environment ---------------------------------
        snapshot = await self._load_latest_snapshot(plant_id)
        env = self._to_room_env(snapshot)

        # ---- 3. candidate pool (all species profiles) --------------------
        candidates = await self._load_candidates()

        # ---- 4. filter: score, sort, exclude self ------------------------
        all_results = filter_companions(
            candidates,
            env,
            current_species_id=plant.species_profile_id,
            top_k=len(candidates),   # score all; we post-filter below
        )

        # ---- 5. keep only fully compatible (all assessed dims match), respect top_k
        compatible = [
            r for r in all_results
            if r.assessed_dimensions > 0 and r.score == 1.0
        ][:top_k]

        items = [
            CompanionRecommendationItem(
                species_id=r.candidate.species_id,
                common_name=r.candidate.common_name,
                scientific_name=r.candidate.scientific_name or None,
                compatibility_score=r.score,
                assessed_dimensions=r.assessed_dimensions,
                match_reasons=list(r.reasons),
                caution_notes=list(r.caution_notes),
                is_compatible=r.is_compatible,
            )
            for r in compatible
        ]

        return CompanionRecommendationResponse(
            plant_id=plant_id,
            current_species_id=plant.species_profile_id,
            environment_available=env is not None,
            candidates_assessed=len(all_results),
            recommendations=items,
            source_species_ids=[r.candidate.species_id for r in compatible],
        )

    # ------------------------------------------------------------------

    async def _load_latest_snapshot(
        self, plant_id: uuid.UUID
    ) -> EnvironmentSnapshot | None:
        result = await self.session.execute(
            select(EnvironmentSnapshot)
            .where(EnvironmentSnapshot.plant_id == plant_id)
            .order_by(EnvironmentSnapshot.window_end.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _to_room_env(snapshot: EnvironmentSnapshot | None) -> RoomEnvironment | None:
        if snapshot is None:
            return None
        return RoomEnvironment(
            light_avg_lux=(
                float(snapshot.light_avg_lux)
                if snapshot.light_avg_lux is not None else None
            ),
            humidity_avg_pct=(
                float(snapshot.humidity_avg_pct)
                if snapshot.humidity_avg_pct is not None else None
            ),
            temperature_avg_c=(
                float(snapshot.temperature_avg_c)
                if snapshot.temperature_avg_c is not None else None
            ),
        )

    async def _load_candidates(self) -> list[CompanionCandidate]:
        result = await self.session.execute(select(SpeciesProfile))
        return [self._to_candidate(row) for row in result.scalars().all()]

    @staticmethod
    def _to_candidate(row: SpeciesProfile) -> CompanionCandidate:
        meta: dict = row.metadata_json or {}
        return CompanionCandidate(
            species_id=row.id,
            scientific_name=row.scientific_name or "",
            common_name=row.common_name or row.korean_name,
            light_min_lux=(
                float(row.light_min_lux) if row.light_min_lux is not None else None
            ),
            light_max_lux=(
                float(row.light_max_lux) if row.light_max_lux is not None else None
            ),
            humidity_min_pct=(
                float(row.humidity_min_pct) if row.humidity_min_pct is not None else None
            ),
            humidity_max_pct=(
                float(row.humidity_max_pct) if row.humidity_max_pct is not None else None
            ),
            temperature_min_c=(
                float(row.temperature_min_c) if row.temperature_min_c is not None else None
            ),
            temperature_max_c=(
                float(row.temperature_max_c) if row.temperature_max_c is not None else None
            ),
            is_toxic=bool(meta.get("is_toxic", False)),
            toxic_to_pets=bool(meta.get("toxic_to_pets", False)),
            toxic_to_children=bool(meta.get("toxic_to_children", False)),
        )
