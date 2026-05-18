"""SensorRetentionRepository — TICKET-067.

Deletes raw sensor_readings rows older than a given cutoff.
Does not touch environment_snapshots.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sensor_reading import SensorReading


class SensorRetentionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def delete_before(self, cutoff: datetime, batch_size: int = 10000) -> int:
        """Delete sensor_readings with measured_at < cutoff.

        Deletes in batches to avoid long-running transactions.
        Returns total rows deleted.
        """
        total_deleted = 0
        while True:
            subq = (
                select(SensorReading.id)
                .where(SensorReading.measured_at < cutoff)
                .limit(batch_size)
                .scalar_subquery()
            )
            result = await self.session.execute(
                delete(SensorReading).where(SensorReading.id.in_(subq))
            )
            deleted = result.rowcount
            total_deleted += deleted
            if deleted < batch_size:
                break
        return total_deleted

    async def count_before(self, cutoff: datetime) -> int:
        """Return the number of rows that would be deleted (for preview/test)."""
        result = await self.session.execute(
            select(func.count()).select_from(SensorReading).where(SensorReading.measured_at < cutoff)
        )
        return result.scalar_one()
