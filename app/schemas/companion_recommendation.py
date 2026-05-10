"""Companion recommendation schemas — TICKET-021."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class CompanionRecommendationItem(BaseModel):
    species_id: uuid.UUID
    common_name: str
    scientific_name: str | None
    compatibility_score: float
    assessed_dimensions: int
    match_reasons: list[str]
    caution_notes: list[str]
    is_compatible: bool


class CompanionRecommendationResponse(BaseModel):
    plant_id: uuid.UUID
    current_species_id: uuid.UUID | None
    environment_available: bool
    candidates_assessed: int          # total species evaluated (incl. incompatible)
    recommendations: list[CompanionRecommendationItem]  # compatible only, sorted
    source_species_ids: list[uuid.UUID]  # species_profile IDs of recommended items
