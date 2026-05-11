"""Growth History schemas — TICKET-FINAL."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

HistoryItemType = Literal["care_log", "environment_summary", "character_state"]

_EXAMPLE_PLANT_ID = "b2c3d4e5-f6a7-8901-bcde-f12345678901"


class HistoryItem(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "care_log",
                "timestamp": "2026-05-11T08:00:00Z",
                "title": "물주기",
                "summary": "",
            }
        }
    )

    type: HistoryItemType
    timestamp: datetime
    title: str
    summary: str


class PlantHistoryResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "plant_id": _EXAMPLE_PLANT_ID,
                "items": [],
            }
        }
    )

    plant_id: uuid.UUID
    items: list[HistoryItem]
