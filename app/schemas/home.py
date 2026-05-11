"""Home Plant Card API schemas — TICKET-009."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict

from app.rules.types import CareStatus, PrimaryAction

_EXAMPLE_PLANT_ID = "b2c3d4e5-f6a7-8901-bcde-f12345678901"
_EXAMPLE_USER_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


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
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "plant_id": _EXAMPLE_PLANT_ID,
                "nickname": "초록이",
                "room_name": "거실",
                "species_name": "몬스테라",
                "character": {
                    "mood": "happy",
                    "expression": "smile",
                    "status_message": "물을 줬더니 기분이 좋아요!",
                    "primary_action": "none",
                    "reason_code": "watered_recently",
                },
                "environment": {
                    "soil_moisture_avg_pct": 65.0,
                    "light_avg_lux": 800.0,
                    "humidity_avg_pct": 55.0,
                    "temperature_avg_c": 22.0,
                },
                "today_recommended_action": "none",
                "care_status": "good",
            }
        }
    )

    plant_id: uuid.UUID
    nickname: str
    room_name: str | None
    species_name: str | None  # korean_name from species_profile, null if unknown
    character: CharacterSummary
    environment: EnvironmentBlock | None  # null when no snapshot in DB
    today_recommended_action: PrimaryAction
    care_status: CareStatus


class HomeResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": _EXAMPLE_USER_ID,
                "plants": [],
            }
        }
    )

    user_id: uuid.UUID
    plants: list[PlantHomeCard]
