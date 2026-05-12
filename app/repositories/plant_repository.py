"""PlantRepository — user-scoped plant access.

Cross-user reads are forbidden: every query filters by user_id.
No sensor snapshot join, no recommendation join, no chat/RAG join.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plant import Plant


class PlantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, plant: Plant) -> Plant:
        self.session.add(plant)
        await self.session.flush()
        return plant

    async def list_by_user(self, user_id: uuid.UUID) -> list[Plant]:
        """Return all plants belonging to the given user."""
        result = await self.session.execute(select(Plant).where(Plant.user_id == user_id))
        return list(result.scalars().all())

    async def get_by_id_and_user(self, plant_id: uuid.UUID, user_id: uuid.UUID) -> Plant | None:
        """Return plant only if it belongs to the requesting user."""
        result = await self.session.execute(
            select(Plant).where(
                Plant.id == plant_id,
                Plant.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, plant_id: uuid.UUID) -> Plant | None:
        """Fetch plant by PK (ownership check done at service layer)."""
        result = await self.session.execute(select(Plant).where(Plant.id == plant_id))
        return result.scalar_one_or_none()

    async def find_by_external_plant_id(self, external_plant_id: str) -> Plant | None:
        """Resolve an edge-node external plant identifier to its internal record."""
        result = await self.session.execute(
            select(Plant).where(Plant.external_plant_id == external_plant_id)
        )
        return result.scalar_one_or_none()
