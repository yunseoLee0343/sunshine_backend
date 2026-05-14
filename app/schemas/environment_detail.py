"""Environment Detail API schemas — TICKET-010."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class MetricStats(BaseModel):
    avg: float | None
    min: float | None
    max: float | None


class WindowSnapshot(BaseModel):
    window: str  # "latest" | "24h" | "7d"
    window_start: datetime
    window_end: datetime
    temperature_c: MetricStats
    humidity_pct: MetricStats
    light_lux: MetricStats
    soil_moisture_pct: MetricStats
    source: str | None = None  # "snapshot" | "raw_sensor_reading_fallback"
    sample_count: int | None = None


class CharacterExplanation(BaseModel):
    reason_code: str
    explanation: str


class EnvironmentDetailResponse(BaseModel):
    plant_id: uuid.UUID
    nickname: str
    room_name: str | None
    latest: WindowSnapshot | None  # null when no snapshot exists
    summary_24h: WindowSnapshot | None
    summary_7d: WindowSnapshot | None
    character_explanation: CharacterExplanation | None  # null when no character history
