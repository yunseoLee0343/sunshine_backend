"""Care Log API schemas — TICKET-011."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

ActionType = Literal["watering", "note"]


class CareLogRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: uuid.UUID
    action_type: ActionType
    note: str | None = None
    acted_at: datetime

    @field_validator("acted_at")
    @classmethod
    def require_timezone(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("acted_at must be timezone-aware")
        return v


class CharacterBlock(BaseModel):
    mood: str
    expression: str
    status_message: str
    primary_action: str
    reason_code: str


class CareLogItem(BaseModel):
    log_id: uuid.UUID
    plant_id: uuid.UUID
    action_type: str
    note: str | None
    acted_at: datetime
    created_at: datetime


_EXAMPLE_PLANT_ID = "b2c3d4e5-f6a7-8901-bcde-f12345678901"
_EXAMPLE_LOG = {
    "log_id": "e5f6a7b8-c9d0-1234-efab-345678901234",
    "plant_id": _EXAMPLE_PLANT_ID,
    "action_type": "watering",
    "note": None,
    "acted_at": "2026-05-11T08:00:00Z",
    "created_at": "2026-05-11T08:00:01Z",
}
_EXAMPLE_CHARACTER = {
    "mood": "happy",
    "expression": "smile",
    "status_message": "물을 줬더니 기분이 좋아요!",
    "primary_action": "none",
    "reason_code": "watered_recently",
}


class CareLogCreateResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "log": _EXAMPLE_LOG,
                "character": _EXAMPLE_CHARACTER,
            }
        }
    )

    log: CareLogItem
    character: CharacterBlock | None  # populated for watering; null for note


class CareLogListResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "plant_id": _EXAMPLE_PLANT_ID,
                "logs": [],
            }
        }
    )

    plant_id: uuid.UUID
    logs: list[CareLogItem]
