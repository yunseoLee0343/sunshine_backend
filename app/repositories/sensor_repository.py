"""SensorRepository — TICKET-005.

Read/write for sensor_readings only. No snapshots, no character updates,
no Rule Engine, no MQTT, no worker enqueue.
"""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sensor_reading import SensorReading


class SensorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_reading_id(self, reading_id: str) -> SensorReading | None:
        result = await self.session.execute(
            select(SensorReading).where(SensorReading.reading_id == reading_id)
        )
        return result.scalar_one_or_none()

    async def insert(
        self,
        *,
        reading_id: str,
        device_id: str,
        plant_id: uuid.UUID,
        measured_at: datetime,
        temperature_c: float,
        humidity_pct: float,
        light_lux: float,
        soil_moisture_pct: float,
        created_at: datetime,
    ) -> SensorReading:
        row = SensorReading(
            id=uuid.uuid4(),
            reading_id=reading_id,
            device_id=device_id,
            plant_id=plant_id,
            measured_at=measured_at,
            temperature_c=temperature_c,
            humidity_pct=humidity_pct,
            light_lux=light_lux,
            soil_moisture_pct=soil_moisture_pct,
            created_at=created_at,
        )
        self.session.add(row)
        await self.session.flush()
        return row
