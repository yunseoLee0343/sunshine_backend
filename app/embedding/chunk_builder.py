"""Deterministic text-chunk builder — TICKET-014B.

Pure functions only. No DB access, no LLM, no I/O.
Each build_* function assembles a fixed-format Korean text string from
14A relational model instances. None-valued fields are omitted.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import TYPE_CHECKING

from app.domain.chunk import CHUNK_KINDS, BuiltChunk, ChunkKind

if TYPE_CHECKING:
    from app.models.plant_care_requirement import PlantCareRequirement
    from app.models.plant_knowledge_entry import PlantKnowledgeEntry
    from app.models.plant_pest_reference import PlantPestReference
    from app.models.plant_placement import PlantPlacement
    from app.models.plant_seasonal_watering import PlantSeasonalWatering
    from app.models.plant_visual_trait import PlantVisualTrait


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _line(label: str, value: str | None) -> str:
    """Return 'label: value.' or '' when value is absent."""
    v = value.strip() if value else None
    return f"{label}: {v}." if v else ""


def _join_lines(*parts: str) -> str:
    return " ".join(p for p in parts if p)


# ---------------------------------------------------------------------------
# Per-kind builders (pure, no DB)
# ---------------------------------------------------------------------------


def build_identity(entry: PlantKnowledgeEntry) -> str:
    head = f"{entry.korean_name}"
    if entry.scientific_name:
        head += f" ({entry.scientific_name})"
    head += " 식물입니다."
    return _join_lines(
        head,
        _line("영문명", entry.common_name),
        _line("과명", entry.family),
        _line("원산지", entry.origin),
    )


def build_care_requirement(
    entry: PlantKnowledgeEntry,
    care: PlantCareRequirement | None,
) -> str:
    if care is None:
        return f"{entry.korean_name} 식물의 관리 정보가 없습니다."
    return _join_lines(
        f"{entry.korean_name} 식물 관리 방법.",
        _line("생육온도", care.growth_temp_text),
        _line("광요구도", care.light_requirement),
        _line("물주기", care.watering_frequency),
        _line("토양", care.soil_type),
        _line("비료", care.fertilizer_info),
    )


def build_seasonal_watering(
    entry: PlantKnowledgeEntry,
    watering: PlantSeasonalWatering | None,
) -> str:
    if watering is None:
        return f"{entry.korean_name} 식물의 계절별 물주기 정보가 없습니다."
    return _join_lines(
        f"{entry.korean_name} 식물 계절별 물주기.",
        _line("봄", watering.spring),
        _line("여름", watering.summer),
        _line("가을", watering.autumn),
        _line("겨울", watering.winter),
    )


def build_pest_reference(
    entry: PlantKnowledgeEntry,
    pest: PlantPestReference | None,
) -> str:
    if pest is None:
        return f"{entry.korean_name} 식물의 병충해 정보가 없습니다."
    terms = pest.parsed_pest_terms or []
    terms_text = ", ".join(str(t) for t in terms) if terms else None
    return _join_lines(
        f"{entry.korean_name} 식물 병충해 및 질병 정보.",
        _line("병충해", pest.pest_text),
        _line("질병", pest.disease_text),
        _line("관련 해충 목록", terms_text),
    )


def build_visual_trait(
    entry: PlantKnowledgeEntry,
    visual: PlantVisualTrait | None,
) -> str:
    if visual is None:
        return f"{entry.korean_name} 식물의 외형 정보가 없습니다."
    return _join_lines(
        f"{entry.korean_name} 식물 외형 특성.",
        _line("잎 색상", visual.leaf_color),
        _line("잎 형태", visual.leaf_shape),
        _line("꽃 색상", visual.flower_color),
        _line("개화기", visual.flower_season),
        _line("초장", visual.height_text),
    )


def build_placement(
    entry: PlantKnowledgeEntry,
    placement: PlantPlacement | None,
) -> str:
    if placement is None:
        return f"{entry.korean_name} 식물의 배치 정보가 없습니다."
    if placement.is_toxic is True:
        toxicity = "있음"
    elif placement.is_toxic is False:
        toxicity = "없음"
    else:
        toxicity = None
    return _join_lines(
        f"{entry.korean_name} 식물 배치 및 독성 정보.",
        _line("배치 장소", placement.placement_locations),
        _line("독성", toxicity),
        _line("독성 설명", placement.toxicity_detail),
        _line("향기", placement.fragrance),
    )


# ---------------------------------------------------------------------------
# Aggregate builder
# ---------------------------------------------------------------------------

_BUILDERS = {
    "identity": lambda e, c, w, p, v, pl: build_identity(e),
    "care_requirement": lambda e, c, w, p, v, pl: build_care_requirement(e, c),
    "seasonal_watering": lambda e, c, w, p, v, pl: build_seasonal_watering(e, w),
    "pest_reference": lambda e, c, w, p, v, pl: build_pest_reference(e, p),
    "visual_trait": lambda e, c, w, p, v, pl: build_visual_trait(e, v),
    "placement": lambda e, c, w, p, v, pl: build_placement(e, pl),
}


def build_all_chunks(
    entry: PlantKnowledgeEntry,
    care: PlantCareRequirement | None,
    watering: PlantSeasonalWatering | None,
    pest: PlantPestReference | None,
    visual: PlantVisualTrait | None,
    placement: PlantPlacement | None,
) -> list[BuiltChunk]:
    chunks: list[BuiltChunk] = []
    for kind in CHUNK_KINDS:
        text = _BUILDERS[kind](entry, care, watering, pest, visual, placement)
        chunks.append(
            BuiltChunk(
                plant_knowledge_id=entry.id,
                chunk_kind=kind,
                text=text,
                text_hash=_hash(text),
            )
        )
    return chunks
