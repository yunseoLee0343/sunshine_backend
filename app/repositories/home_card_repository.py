"""HomeCardRepository — TICKET-009.

Read-only queries assembled specifically for the home-card endpoints.
Never writes to or mutates any table.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plant import Plant
from app.models.plant_character import PlantCharacter
from app.models.species_profile import SpeciesProfile


class HomeCardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_plants_by_user(self, user_id: uuid.UUID) -> list[Plant]:
        result = await self.session.execute(select(Plant).where(Plant.user_id == user_id))
        return list(result.scalars().all())

    async def get_plant_for_user(self, plant_id: uuid.UUID, user_id: uuid.UUID) -> Plant | None:
        """Return plant only if it belongs to the requesting user; None otherwise."""
        result = await self.session.execute(
            select(Plant).where(
                Plant.id == plant_id,
                Plant.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_species_profile(self, species_profile_id: uuid.UUID) -> SpeciesProfile | None:
        return await self.session.get(SpeciesProfile, species_profile_id)

    async def get_latest_character(self, plant_id: uuid.UUID) -> PlantCharacter | None:
        """Return the most recently created character row; None if none exist."""
        result = await self.session.execute(
            select(PlantCharacter)
            .where(PlantCharacter.plant_id == plant_id)
            .order_by(PlantCharacter.created_at.desc(), PlantCharacter.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
