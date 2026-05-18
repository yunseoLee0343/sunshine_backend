"""sensor_retention — TICKET-067.

CLI entry point to delete raw sensor_readings older than the retention window.

Production sequence:
  1. Run TICKET-068 rollup to compact old raw data into environment_snapshots.
  2. Run this command to delete raw rows older than SENSOR_RAW_RETENTION_DAYS.

Usage:
  python -m app.ops.sensor_retention
"""

from __future__ import annotations

import asyncio
import json
import sys

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.services.sensor_retention_service import SensorRetentionService


async def _run() -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        svc = SensorRetentionService(session)
        result = await svc.run()
        await session.commit()

    await engine.dispose()

    output = {
        "retention_days": result.retention_days,
        "cutoff": result.cutoff.isoformat(),
        "deleted_count": result.deleted_count,
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    asyncio.run(_run())
    sys.exit(0)
