"""PlantSensorDeviceRepository — TICKET-066."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plant_sensor_device import PlantSensorDevice


class PlantSensorDeviceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_active(self, plant_id: uuid.UUID, device_id: str) -> PlantSensorDevice | None:
        """Return active device mapping for (plant_id, device_id), or None."""
        result = await self.session.execute(
            select(PlantSensorDevice).where(
                PlantSensorDevice.plant_id == plant_id,
                PlantSensorDevice.device_id == device_id,
                PlantSensorDevice.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()
