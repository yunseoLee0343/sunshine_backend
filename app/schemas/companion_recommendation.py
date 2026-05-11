"""Companion recommendation schemas — TICKET-021."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict

_EXAMPLE_PLANT_ID = "b2c3d4e5-f6a7-8901-bcde-f12345678901"
_EXAMPLE_SPECIES_ID = "c3d4e5f6-a7b8-9012-cdef-123456789012"


class CompanionRecommendationItem(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "species_id": _EXAMPLE_SPECIES_ID,
                "common_name": "Pothos",
                "scientific_name": "Epipremnum aureum",
                "compatibility_score": 0.85,
                "assessed_dimensions": 3,
                "match_reasons": ["비슷한 빛 요구량", "비슷한 습도 선호"],
                "caution_notes": [],
                "is_compatible": True,
            }
        }
    )

    species_id: uuid.UUID
    common_name: str
    scientific_name: str | None
    compatibility_score: float
    assessed_dimensions: int
    match_reasons: list[str]
    caution_notes: list[str]
    is_compatible: bool


class CompanionRecommendationResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "plant_id": _EXAMPLE_PLANT_ID,
                "current_species_id": _EXAMPLE_SPECIES_ID,
                "environment_available": True,
                "candidates_assessed": 10,
                "recommendations": [],
                "source_species_ids": [],
            }
        }
    )

    plant_id: uuid.UUID
    current_species_id: uuid.UUID | None
    environment_available: bool
    candidates_assessed: int  # total species evaluated (incl. incompatible)
    recommendations: list[CompanionRecommendationItem]  # compatible only, sorted
    source_species_ids: list[uuid.UUID]  # species_profile IDs of recommended items
