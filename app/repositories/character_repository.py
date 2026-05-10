"""CharacterRepository — append-only history of plant character states.

Every state change is persisted as a new ``plant_characters`` row. Old rows
are never updated or deleted; the latest state is the row with the greatest
``created_at`` (then ``id`` as deterministic tiebreaker).
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plant_character import PlantCharacter


class CharacterRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, character: PlantCharacter) -> PlantCharacter:
        """Insert a new character row. Never updates an existing row."""
        self.session.add(character)
        await self.session.flush()
        return character

    async def get_latest_for_plant(self, plant_id: uuid.UUID) -> PlantCharacter | None:
        """Return the most recently created character row for the plant."""
        result = await self.session.execute(
            select(PlantCharacter)
            .where(PlantCharacter.plant_id == plant_id)
            .order_by(PlantCharacter.created_at.desc(), PlantCharacter.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_for_plant(self, plant_id: uuid.UUID) -> list[PlantCharacter]:
        """Return all character rows for the plant in append order (oldest first)."""
        result = await self.session.execute(
            select(PlantCharacter)
            .where(PlantCharacter.plant_id == plant_id)
            .order_by(PlantCharacter.created_at.asc(), PlantCharacter.id.asc())
        )
        return list(result.scalars().all())
