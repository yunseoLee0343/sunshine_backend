"""SensorIngestService — TICKET-005.

Ingest a single sensor reading. Idempotent by reading_id:
  - New reading_id   → INSERT, return 201 "inserted"
  - Duplicate        → no-op,  return 200 "duplicate_ignored"
  - Unknown plant_id → raise 404

Forbidden: snapshots, character updates, Rule Engine, MQTT, workers.
"""

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plant import Plant
from app.repositories.sensor_repository import SensorRepository
from app.schemas.sensor_readings import SensorReadingRequest, SensorReadingResponse


class SensorIngestService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = SensorRepository(session)

    async def ingest(self, req: SensorReadingRequest) -> tuple[SensorReadingResponse, int]:
        """Return (response, http_status_code)."""
        # 1. Validate plant exists.
        plant = await self.session.get(Plant, req.plant_id)
        if plant is None:
            raise HTTPException(status_code=404, detail="plant not found")

        # 2. Idempotency check.
        existing = await self.repo.find_by_reading_id(req.reading_id)
        if existing is not None:
            return (
                SensorReadingResponse(
                    status="duplicate_ignored",
                    ignored=True,
                    reading_id=req.reading_id,
                ),
                200,
            )

        # 3. Insert new row.
        await self.repo.insert(
            reading_id=req.reading_id,
            device_id=req.device_id,
            plant_id=req.plant_id,
            measured_at=req.measured_at,
            temperature_c=req.temperature_c,
            humidity_pct=req.humidity_pct,
            light_lux=req.light_lux,
            soil_moisture_pct=req.soil_moisture_pct,
            created_at=datetime.now(UTC),
        )
        await self.session.commit()

        return (
            SensorReadingResponse(
                status="inserted",
                ignored=False,
                reading_id=req.reading_id,
            ),
            201,
        )
