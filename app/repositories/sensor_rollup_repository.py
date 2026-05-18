"""SensorRollupRepository — TICKET-068."""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sensor_metric_rollup import SensorMetricRollup
from app.models.sensor_reading import SensorReading

_METRICS = ("temperature_c", "humidity_pct", "light_lux", "soil_moisture_pct")


@dataclass
class RollupBucket:
    plant_id: uuid.UUID
    metric_name: str
    bucket: str
    bucket_start: datetime
    bucket_end: datetime
    avg_value: float | None
    min_value: float | None
    max_value: float | None
    sample_count: int


def _floor_hour(ts: datetime) -> datetime:
    return ts.replace(minute=0, second=0, microsecond=0)


class SensorRollupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_rollups_in_range(
        self,
        plant_id: uuid.UUID,
        metric_name: str,
        bucket: str,
        start: datetime,
        end: datetime,
    ) -> list[SensorMetricRollup]:
        """Return hourly rollup rows where bucket_start >= start and bucket_end <= end."""
        result = await self.session.execute(
            select(SensorMetricRollup).where(
                SensorMetricRollup.plant_id == plant_id,
                SensorMetricRollup.metric_name == metric_name,
                SensorMetricRollup.bucket == bucket,
                SensorMetricRollup.bucket_start >= start,
                SensorMetricRollup.bucket_end <= end,
            )
        )
        return list(result.scalars().all())

    async def upsert_rollup(
        self,
        *,
        plant_id: uuid.UUID,
        metric_name: str,
        bucket: str,
        bucket_start: datetime,
        bucket_end: datetime,
        avg_value: float | None,
        min_value: float | None,
        max_value: float | None,
        sample_count: int,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        values = dict(
            id=uuid.uuid4(),
            plant_id=plant_id,
            metric_name=metric_name,
            bucket=bucket,
            bucket_start=bucket_start,
            bucket_end=bucket_end,
            avg_value=avg_value,
            min_value=min_value,
            max_value=max_value,
            sample_count=sample_count,
            created_at=created_at,
            updated_at=updated_at,
        )
        update_cols = {k: v for k, v in values.items() if k not in {"id", "created_at"}}
        stmt = (
            pg_insert(SensorMetricRollup)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["plant_id", "metric_name", "bucket", "bucket_start", "bucket_end"],
                set_=update_cols,
            )
        )
        await self.session.execute(stmt)

    async def rollup_raw_readings(
        self,
        plant_id: uuid.UUID,
        start: datetime,
        end: datetime,
    ) -> list[RollupBucket]:
        """Aggregate raw sensor_readings in [start, end) into hourly RollupBucket objects.

        Null metric values are skipped. Returns one entry per
        (metric_name, bucket_start) pair that has at least one non-null value.
        """
        result = await self.session.execute(
            select(SensorReading).where(
                SensorReading.plant_id == plant_id,
                SensorReading.measured_at >= start,
                SensorReading.measured_at < end,
            )
        )
        readings = list(result.scalars().all())

        # key: (metric_name, bucket_start_floored_to_hour)
        buckets: dict[tuple[str, datetime], list[float]] = defaultdict(list)
        for r in readings:
            bs = _floor_hour(r.measured_at)
            for metric in _METRICS:
                v = getattr(r, metric)
                if v is not None:
                    buckets[(metric, bs)].append(float(v))

        out: list[RollupBucket] = []
        for (metric, bs), values in sorted(buckets.items(), key=lambda kv: (kv[0][0], kv[0][1])):
            be = bs + timedelta(hours=1)
            out.append(
                RollupBucket(
                    plant_id=plant_id,
                    metric_name=metric,
                    bucket="hourly",
                    bucket_start=bs,
                    bucket_end=be,
                    avg_value=sum(values) / len(values),
                    min_value=min(values),
                    max_value=max(values),
                    sample_count=len(values),
                )
            )
        return out
