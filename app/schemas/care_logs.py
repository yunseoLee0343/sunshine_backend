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


class CareLogCreateResponse(BaseModel):
    log: CareLogItem
    character: CharacterBlock | None   # populated for watering; null for note


class CareLogListResponse(BaseModel):
    plant_id: uuid.UUID
    logs: list[CareLogItem]
