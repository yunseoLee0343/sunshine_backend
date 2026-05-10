"""Home Plant Card API schemas — TICKET-009."""

from __future__ import annotations

import uuid

from pydantic import BaseModel

from app.rules.types import CareStatus, PrimaryAction


class EnvironmentBlock(BaseModel):
    """Latest sensor averages. All fields None when no snapshot exists."""

    soil_moisture_avg_pct: float | None
    light_avg_lux: float | None
    humidity_avg_pct: float | None
    temperature_avg_c: float | None


class CharacterSummary(BaseModel):
    mood: str
    expression: str
    status_message: str
    primary_action: str
    reason_code: str


class PlantHomeCard(BaseModel):
    plant_id: uuid.UUID
    nickname: str
    room_name: str | None
    species_name: str | None          # korean_name from species_profile, null if unknown
    character: CharacterSummary
    environment: EnvironmentBlock | None  # null when no snapshot in DB
    today_recommended_action: PrimaryAction
    care_status: CareStatus


class HomeResponse(BaseModel):
    user_id: uuid.UUID
    plants: list[PlantHomeCard]
