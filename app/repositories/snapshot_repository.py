"""SnapshotRepository — TICKET-007.

Read sensor_readings for aggregation; upsert environment_snapshots.
No judgment logic, no character updates, no Rule Engine.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.environment_snapshot import EnvironmentSnapshot
from app.models.sensor_reading import SensorReading


class SnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # sensor_readings queries (read-only)
    # ------------------------------------------------------------------

    async def get_latest_reading(
        self, plant_id: uuid.UUID, before: datetime
    ) -> SensorReading | None:
        """Return the single most recent reading with measured_at <= before."""
        result = await self.session.execute(
            select(SensorReading)
            .where(
                SensorReading.plant_id == plant_id,
                SensorReading.measured_at <= before,
            )
            .order_by(SensorReading.measured_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_readings_in_range(
        self,
        plant_id: uuid.UUID,
        start: datetime,
        end: datetime,
    ) -> list[SensorReading]:
        """Return all readings where start <= measured_at <= end."""
        result = await self.session.execute(
            select(SensorReading).where(
                SensorReading.plant_id == plant_id,
                SensorReading.measured_at >= start,
                SensorReading.measured_at <= end,
            )
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # environment_snapshots upsert
    # ------------------------------------------------------------------

    async def upsert(
        self,
        *,
        plant_id: uuid.UUID,
        window: str,
        window_start: datetime,
        window_end: datetime,
        temperature_avg_c: float | None,
        temperature_min_c: float | None,
        temperature_max_c: float | None,
        humidity_avg_pct: float | None,
        humidity_min_pct: float | None,
        humidity_max_pct: float | None,
        light_avg_lux: float | None,
        light_min_lux: float | None,
        light_max_lux: float | None,
        soil_moisture_avg_pct: float | None,
        soil_moisture_min_pct: float | None,
        soil_moisture_max_pct: float | None,
        created_at: datetime,
    ) -> None:
        """INSERT or UPDATE on (plant_id, window, window_start, window_end)."""
        values = dict(
            id=uuid.uuid4(),
            plant_id=plant_id,
            window=window,
            window_start=window_start,
            window_end=window_end,
            temperature_avg_c=temperature_avg_c,
            temperature_min_c=temperature_min_c,
            temperature_max_c=temperature_max_c,
            humidity_avg_pct=humidity_avg_pct,
            humidity_min_pct=humidity_min_pct,
            humidity_max_pct=humidity_max_pct,
            light_avg_lux=light_avg_lux,
            light_min_lux=light_min_lux,
            light_max_lux=light_max_lux,
            soil_moisture_avg_pct=soil_moisture_avg_pct,
            soil_moisture_min_pct=soil_moisture_min_pct,
            soil_moisture_max_pct=soil_moisture_max_pct,
            created_at=created_at,
        )
        update_cols = {k: v for k, v in values.items() if k not in {"id"}}
        stmt = (
            pg_insert(EnvironmentSnapshot)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["plant_id", "window", "window_start", "window_end"],
                set_=update_cols,
            )
        )
        await self.session.execute(stmt)
