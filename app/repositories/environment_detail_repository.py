"""EnvironmentDetailRepository — TICKET-010.

Read-only queries for the environment detail endpoint.
Never writes, never aggregates raw sensor readings.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.environment_snapshot import EnvironmentSnapshot
from app.models.plant import Plant
from app.models.plant_character import PlantCharacter
from app.models.sensor_reading import SensorReading


class EnvironmentDetailRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_plant_for_user(self, plant_id: uuid.UUID, user_id: uuid.UUID) -> Plant | None:
        """Return plant only when it belongs to the requesting user."""
        result = await self.session.execute(
            select(Plant).where(
                Plant.id == plant_id,
                Plant.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_snapshot_by_window(self, plant_id: uuid.UUID, window: str) -> EnvironmentSnapshot | None:
        """Return the most recently created snapshot for the given window name."""
        result = await self.session.execute(
            select(EnvironmentSnapshot)
            .where(
                EnvironmentSnapshot.plant_id == plant_id,
                EnvironmentSnapshot.window == window,
            )
            .order_by(EnvironmentSnapshot.window_end.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_sensor_reading(self, plant_id: uuid.UUID) -> SensorReading | None:
        """Return the single most recent sensor reading for the plant."""
        result = await self.session.execute(
            select(SensorReading)
            .where(SensorReading.plant_id == plant_id)
            .order_by(SensorReading.measured_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_character(self, plant_id: uuid.UUID) -> PlantCharacter | None:
        result = await self.session.execute(
            select(PlantCharacter)
            .where(PlantCharacter.plant_id == plant_id)
            .order_by(PlantCharacter.created_at.desc(), PlantCharacter.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
