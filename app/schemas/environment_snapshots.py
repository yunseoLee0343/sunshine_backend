"""Environment Snapshot DTOs — TICKET-007."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

WindowName = Literal["latest", "24h", "7d"]
SnapshotStatus = Literal["ok", "missing_data"]


class MetricStats(BaseModel):
    avg: float | None
    min: float | None
    max: float | None


class EnvironmentSnapshotResult(BaseModel):
    plant_id: uuid.UUID
    window: WindowName
    window_start: datetime
    window_end: datetime
    status: SnapshotStatus
    sample_count: int
    temperature_c: MetricStats
    humidity_pct: MetricStats
    light_lux: MetricStats
    soil_moisture_pct: MetricStats


class AggregationSummary(BaseModel):
    plant_id: uuid.UUID
    computed_at: datetime
    snapshots: list[EnvironmentSnapshotResult]
