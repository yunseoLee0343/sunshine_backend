"""sensor_rollup — TICKET-068.

CLI entry point to roll up raw sensor_readings into hourly sensor_metric_rollups
for all plants.

Production sequence:
  1. Run this command to roll up raw data older than 2 days.
  2. Run SnapshotService.aggregate() to update environment_snapshots.
  3. Run sensor_retention to delete raw readings older than 2 days.

Usage:
  python -m app.ops.sensor_rollup
"""

from __future__ import annotations

import asyncio
import json
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.plant import Plant
from app.services.sensor_rollup_service import SensorRollupService


async def _run() -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        result = await session.execute(select(Plant.id))
        plant_ids = list(result.scalars().all())

        svc = SensorRollupService(session)
        total = 0
        for plant_id in plant_ids:
            summary = await svc.rollup(plant_id)
            total += summary.created_or_updated

        await session.commit()

    await engine.dispose()

    print(json.dumps({
        "plants_processed": len(plant_ids),
        "total_rollups_created_or_updated": total,
    }, indent=2))


if __name__ == "__main__":
    asyncio.run(_run())
    sys.exit(0)
