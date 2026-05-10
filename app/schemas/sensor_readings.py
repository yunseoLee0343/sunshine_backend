"""Sensor Reading schemas — TICKET-005."""

import math
import re
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

_READING_ID_RE = re.compile(r"^[A-Za-z0-9\-_:.]+$")


def _reject_non_finite(v: float, name: str) -> float:
    if math.isnan(v) or math.isinf(v):
        raise ValueError(f"{name} must be a finite number")
    return v


class SensorReadingRequest(BaseModel):
    reading_id: str = Field(..., min_length=1, max_length=128)
    device_id: str = Field(..., min_length=1, max_length=128)
    plant_id: uuid.UUID
    measured_at: datetime
    temperature_c: float = Field(..., ge=-40.0, le=80.0)
    humidity_pct: float = Field(..., ge=0.0, le=100.0)
    light_lux: float = Field(..., ge=0.0, le=200_000.0)
    soil_moisture_pct: float = Field(..., ge=0.0, le=100.0)

    @field_validator("reading_id")
    @classmethod
    def reading_id_charset(cls, v: str) -> str:
        if not _READING_ID_RE.match(v):
            raise ValueError(
                "reading_id may only contain alphanumeric characters, "
                "dashes, underscores, colons, and dots"
            )
        return v

    @field_validator("measured_at")
    @classmethod
    def measured_at_must_be_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError("measured_at must be timezone-aware")
        return v

    @model_validator(mode="after")
    def reject_non_finite_numbers(self) -> "SensorReadingRequest":
        _reject_non_finite(self.temperature_c, "temperature_c")
        _reject_non_finite(self.humidity_pct, "humidity_pct")
        _reject_non_finite(self.light_lux, "light_lux")
        _reject_non_finite(self.soil_moisture_pct, "soil_moisture_pct")
        return self


class SensorReadingResponse(BaseModel):
    status: str        # "inserted" | "duplicate_ignored"
    ignored: bool
    reading_id: str
