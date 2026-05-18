"""SensorRollupService — TICKET-068.

Builds hourly sensor_metric_rollups from raw sensor_readings.

Production pipeline order:
  1. Roll up raw readings older than 2 days (this service).
  2. Update environment_snapshots (SnapshotService.aggregate).
  3. Delete raw readings older than 2 days (SensorRetentionService.run).

Never delete raw rows before they have been rolled up.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.sensor_rollup_repository import SensorRollupRepository

_ROLLUP_HORIZON_DAYS = 7


@dataclass
class RollupSummary:
    bucket: str
    created_or_updated: int
    range_start: datetime
    range_end: datetime


class SensorRollupService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = SensorRollupRepository(session)

    async def rollup(
        self,
        plant_id: uuid.UUID,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> RollupSummary:
        """Create or update hourly rollups for a plant in [start, end).

        Defaults to rolling up the past ROLLUP_HORIZON_DAYS of raw data.
        Idempotent: re-running produces the same result.
        """
        now = datetime.now(UTC)
        if end is None:
            end = now
        if start is None:
            start = end - timedelta(days=_ROLLUP_HORIZON_DAYS)

        buckets = await self.repo.rollup_raw_readings(plant_id, start, end)
        ts = datetime.now(UTC)
        for b in buckets:
            await self.repo.upsert_rollup(
                plant_id=b.plant_id,
                metric_name=b.metric_name,
                bucket=b.bucket,
                bucket_start=b.bucket_start,
                bucket_end=b.bucket_end,
                avg_value=b.avg_value,
                min_value=b.min_value,
                max_value=b.max_value,
                sample_count=b.sample_count,
                created_at=ts,
                updated_at=ts,
            )
        return RollupSummary(
            bucket="hourly",
            created_or_updated=len(buckets),
            range_start=start,
            range_end=end,
        )
