"""SnapshotService — TICKET-007.

Aggregates sensor_readings into environment_snapshots for three windows:
  latest  — single most recent reading at or before `now`
  24h     — readings in [now-24h, now]
  7d      — readings in [now-7d, now]

Rules:
  - No data in a window → status "missing_data", nothing persisted.
  - Data exists → compute avg/min/max, upsert, status "ok".
  - Upsert key: (plant_id, window, window_start, window_end).
  - No Rule Engine, no character updates, no LLM/RAG.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sensor_reading import SensorReading
from app.repositories.snapshot_repository import SnapshotRepository
from app.schemas.environment_snapshots import (
    AggregationSummary,
    EnvironmentSnapshotResult,
    MetricStats,
    SnapshotStatus,
)

_24H = timedelta(hours=24)
_7D = timedelta(days=7)


def _stats(readings: list[SensorReading], attr: str) -> MetricStats:
    values = [float(getattr(r, attr)) for r in readings]
    if not values:
        return MetricStats(avg=None, min=None, max=None)
    return MetricStats(
        avg=sum(values) / len(values),
        min=min(values),
        max=max(values),
    )


def _build_result(
    plant_id: uuid.UUID,
    window: str,
    window_start: datetime,
    window_end: datetime,
    readings: list[SensorReading],
) -> EnvironmentSnapshotResult:
    status: SnapshotStatus = "ok" if readings else "missing_data"
    return EnvironmentSnapshotResult(
        plant_id=plant_id,
        window=window,  # type: ignore[arg-type]
        window_start=window_start,
        window_end=window_end,
        status=status,
        sample_count=len(readings),
        temperature_c=_stats(readings, "temperature_c"),
        humidity_pct=_stats(readings, "humidity_pct"),
        light_lux=_stats(readings, "light_lux"),
        soil_moisture_pct=_stats(readings, "soil_moisture_pct"),
    )


class SnapshotService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = SnapshotRepository(session)

    async def aggregate(
        self,
        plant_id: uuid.UUID,
        now: datetime | None = None,
    ) -> AggregationSummary:
        if now is None:
            now = datetime.now(UTC)

        results: list[EnvironmentSnapshotResult] = []
        created_at = datetime.now(UTC)

        # --- latest ---
        latest_row = await self.repo.get_latest_reading(plant_id, before=now)
        if latest_row is not None:
            ts = latest_row.measured_at
            result = _build_result(plant_id, "latest", ts, ts, [latest_row])
            await self._persist(result, created_at)
        else:
            result = _build_result(plant_id, "latest", now, now, [])
        results.append(result)

        # --- 24h ---
        start_24h = now - _24H
        rows_24h = await self.repo.get_readings_in_range(plant_id, start_24h, now)
        result_24h = _build_result(plant_id, "24h", start_24h, now, rows_24h)
        if rows_24h:
            await self._persist(result_24h, created_at)
        results.append(result_24h)

        # --- 7d ---
        start_7d = now - _7D
        rows_7d = await self.repo.get_readings_in_range(plant_id, start_7d, now)
        result_7d = _build_result(plant_id, "7d", start_7d, now, rows_7d)
        if rows_7d:
            await self._persist(result_7d, created_at)
        results.append(result_7d)

        return AggregationSummary(
            plant_id=plant_id,
            computed_at=created_at,
            snapshots=results,
        )

    async def _persist(self, result: EnvironmentSnapshotResult, created_at: datetime) -> None:
        await self.repo.upsert(
            plant_id=result.plant_id,
            window=result.window,
            window_start=result.window_start,
            window_end=result.window_end,
            temperature_avg_c=result.temperature_c.avg,
            temperature_min_c=result.temperature_c.min,
            temperature_max_c=result.temperature_c.max,
            humidity_avg_pct=result.humidity_pct.avg,
            humidity_min_pct=result.humidity_pct.min,
            humidity_max_pct=result.humidity_pct.max,
            light_avg_lux=result.light_lux.avg,
            light_min_lux=result.light_lux.min,
            light_max_lux=result.light_lux.max,
            soil_moisture_avg_pct=result.soil_moisture_pct.avg,
            soil_moisture_min_pct=result.soil_moisture_pct.min,
            soil_moisture_max_pct=result.soil_moisture_pct.max,
            created_at=created_at,
        )
