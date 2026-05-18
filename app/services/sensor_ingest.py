"""SensorIngestService — TICKET-005 / S-001 / TICKET-053.

Ingest a single sensor reading. Idempotent by reading_id:
  - New reading_id   → INSERT, return 201 "inserted"
  - Duplicate        → no-op,  return 200 "duplicate_ignored"
  - Unknown plant_id → raise 404

plant_id resolution (S-001):
  1. If payload plant_id is a valid UUID → lookup by PK.
  2. Else → lookup by Plant.external_plant_id.
  3. If plant.device_id is set, it must match payload device_id.

Forbidden: snapshots, character updates, Rule Engine, MQTT, workers.
"""

import uuid as _uuid_mod
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plant import Plant
from app.repositories.plant_repository import PlantRepository
from app.repositories.plant_sensor_device_repository import PlantSensorDeviceRepository
from app.repositories.sensor_repository import SensorRepository
from app.schemas.sensor_readings import SensorReadingRequest, SensorReadingResponse


class SensorIngestService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = SensorRepository(session)
        # Set by ingest() after a successful insert; None on duplicate or error.
        self.resolved_plant_id: _uuid_mod.UUID | None = None

    async def _resolve_plant(self, plant_id_str: str, device_id: str) -> Plant | None:
        try:
            pid = _uuid_mod.UUID(plant_id_str)
            plant = await self.session.get(Plant, pid)
        except ValueError:
            plant_repo = PlantRepository(self.session)
            plant = await plant_repo.find_by_external_plant_id(plant_id_str)

        if plant is None:
            return None

        # New: check plant_sensor_devices table for active device mapping.
        device_repo = PlantSensorDeviceRepository(self.session)
        active = await device_repo.find_active(plant.id, device_id)
        if active is not None:
            return plant

        # Legacy fallback: honour plant.device_id if no table row found.
        if plant.device_id is not None and plant.device_id != device_id:
            return None
        return plant

    async def ingest(self, req: SensorReadingRequest) -> tuple[SensorReadingResponse, int]:
        """Return (response, http_status_code).

        After a successful INSERT, `self.resolved_plant_id` is set to the
        internal UUID of the plant so the caller (e.g. MqttSensorIngestService)
        can trigger snapshot aggregation without re-resolving the plant.
        """
        self.resolved_plant_id = None

        # 1. Resolve plant (UUID or external_plant_id).
        plant = await self._resolve_plant(req.plant_id, req.device_id)
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

        # 3. Insert new row — always store the internal UUID, not the external string.
        await self.repo.insert(
            reading_id=req.reading_id,
            device_id=req.device_id,
            plant_id=plant.id,
            measured_at=req.measured_at,
            temperature_c=req.temperature_c,
            humidity_pct=req.humidity_pct,
            light_lux=req.light_lux,
            soil_moisture_pct=req.soil_moisture_pct,
            created_at=datetime.now(UTC),
        )
        # Do NOT commit — the caller owns the transaction boundary.
        # SQLAlchemy autoflush makes this INSERT visible to subsequent
        # SELECTs within the same session before any commit.
        self.resolved_plant_id = plant.id
        return (
            SensorReadingResponse(
                status="inserted",
                ignored=False,
                reading_id=req.reading_id,
            ),
            201,
        )
