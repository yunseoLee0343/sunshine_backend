"""SnapshotService — TICKET-007 / TICKET-068.

Aggregates sensor data into environment_snapshots for three windows:
  latest  — metric-wise latest non-null reading (TICKET-066)
  24h     — raw readings in [now-24h, now]
  7d      — hourly rollups in [now-7d, now]  (TICKET-068)

Rules:
  - No data in a window → status "missing_data", nothing persisted.
  - Data exists → compute avg/min/max, upsert, status "ok".
  - Upsert key: (plant_id, window)  (TICKET-067).
  - No Rule Engine, no character updates, no LLM/RAG.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sensor_reading import SensorReading
from app.repositories.sensor_rollup_repository import SensorRollupRepository
from app.repositories.snapshot_repository import SnapshotRepository
from app.schemas.environment_snapshots import (
    AggregationSummary,
    EnvironmentSnapshotResult,
    MetricStats,
    SnapshotStatus,
)

_24H = timedelta(hours=24)
_7D = timedelta(days=7)
_METRIC_KEYS = ("temperature_c", "humidity_pct", "light_lux", "soil_moisture_pct")


def _stats(readings: list[SensorReading], attr: str) -> MetricStats:
    values = [
        float(value)
        for r in readings
        if (value := getattr(r, attr)) is not None
    ]
    if not values:
        return MetricStats(avg=None, min=None, max=None)
    return MetricStats(
        avg=sum(values) / len(values),
        min=min(values),
        max=max(values),
    )


def _metric_stat(value: float | None) -> MetricStats:
    if value is None:
        return MetricStats(avg=None, min=None, max=None)
    return MetricStats(avg=value, min=value, max=value)


def _rollup_stats(rollups: list) -> MetricStats:
    """Weighted avg/min/max from a list of SensorMetricRollup rows."""
    valid = [r for r in rollups if r.avg_value is not None]
    if not valid:
        return MetricStats(avg=None, min=None, max=None)
    total_count = sum(r.sample_count for r in valid)
    if total_count == 0:
        return MetricStats(avg=None, min=None, max=None)
    avg = sum(float(r.avg_value) * r.sample_count for r in valid) / total_count
    mins = [float(r.min_value) for r in valid if r.min_value is not None]
    maxs = [float(r.max_value) for r in valid if r.max_value is not None]
    return MetricStats(
        avg=avg,
        min=min(mins) if mins else None,
        max=max(maxs) if maxs else None,
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
        self.session = session
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

        # --- latest: metric-wise merge across devices (TICKET-066) ---
        latest_per_metric = await self.repo.get_latest_per_metric(plant_id, before=now)
        any_data = any(row is not None for row in latest_per_metric.values())
        if any_data:
            timestamps = [
                row.measured_at
                for row in latest_per_metric.values()
                if row is not None
            ]
            window_start = min(timestamps)
            window_end = max(timestamps)
            seen_ids = {row.id for row in latest_per_metric.values() if row is not None}

            def _val(key: str) -> float | None:
                r = latest_per_metric[key]
                if r is None:
                    return None
                v = getattr(r, key)
                return float(v) if v is not None else None

            result = EnvironmentSnapshotResult(
                plant_id=plant_id,
                window="latest",
                window_start=window_start,
                window_end=window_end,
                status="ok",
                sample_count=len(seen_ids),
                temperature_c=_metric_stat(_val("temperature_c")),
                humidity_pct=_metric_stat(_val("humidity_pct")),
                light_lux=_metric_stat(_val("light_lux")),
                soil_moisture_pct=_metric_stat(_val("soil_moisture_pct")),
            )
            await self._persist(result, created_at)
        else:
            result = _build_result(plant_id, "latest", now, now, [])
        results.append(result)

        # --- 24h: from raw sensor_readings ---
        start_24h = now - _24H
        rows_24h = await self.repo.get_readings_in_range(plant_id, start_24h, now)
        result_24h = _build_result(plant_id, "24h", start_24h, now, rows_24h)
        if rows_24h:
            await self._persist(result_24h, created_at)
        results.append(result_24h)

        # --- 7d: from sensor_metric_rollups (TICKET-068) ---
        start_7d = now - _7D
        rollup_repo = SensorRollupRepository(self.session)
        metric_rollups = {}
        for attr in _METRIC_KEYS:
            metric_rollups[attr] = await rollup_repo.get_rollups_in_range(
                plant_id, attr, "hourly", start_7d, now
            )
        any_7d = any(metric_rollups[attr] for attr in _METRIC_KEYS)
        if any_7d:
            total_7d_samples = sum(
                r.sample_count for attr in _METRIC_KEYS for r in metric_rollups[attr]
            )
            result_7d = EnvironmentSnapshotResult(
                plant_id=plant_id,
                window="7d",
                window_start=start_7d,
                window_end=now,
                status="ok",
                sample_count=total_7d_samples,
                temperature_c=_rollup_stats(metric_rollups["temperature_c"]),
                humidity_pct=_rollup_stats(metric_rollups["humidity_pct"]),
                light_lux=_rollup_stats(metric_rollups["light_lux"]),
                soil_moisture_pct=_rollup_stats(metric_rollups["soil_moisture_pct"]),
            )
            await self._persist(result_7d, created_at)
        else:
            result_7d = _build_result(plant_id, "7d", start_7d, now, [])
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
