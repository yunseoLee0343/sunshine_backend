"""SensorRetentionService — TICKET-067.

Deletes raw sensor_readings older than SENSOR_RAW_RETENTION_DAYS.

Production sequence (see TICKET-068):
  1. Run TICKET-068 rollup to compact old raw data into snapshots.
  2. Run this service to delete raw rows older than the retention window.
  3. Never delete before rolling up — data loss is permanent.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.sensor_retention_repository import SensorRetentionRepository


@dataclass
class RetentionResult:
    retention_days: int
    cutoff: datetime
    deleted_count: int


class SensorRetentionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = SensorRetentionRepository(session)

    async def run(self, now: datetime | None = None) -> RetentionResult:
        """Delete sensor_readings older than SENSOR_RAW_RETENTION_DAYS.

        Returns a RetentionResult regardless of whether retention is enabled.
        When disabled, deleted_count is 0 and no rows are touched.
        """
        if now is None:
            now = datetime.now(UTC)

        retention_days = settings.SENSOR_RAW_RETENTION_DAYS
        cutoff = now - timedelta(days=retention_days)

        if not settings.SENSOR_RETENTION_ENABLED:
            return RetentionResult(
                retention_days=retention_days,
                cutoff=cutoff,
                deleted_count=0,
            )

        deleted = await self.repo.delete_before(
            cutoff=cutoff,
            batch_size=settings.SENSOR_RETENTION_BATCH_SIZE,
        )
        return RetentionResult(
            retention_days=retention_days,
            cutoff=cutoff,
            deleted_count=deleted,
        )
