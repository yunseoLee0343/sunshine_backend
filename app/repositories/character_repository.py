"""CharacterRepository — initial state creation and latest-state lookup.

Character evolution (Ticket 4 CharacterStateEngine) is not implemented here.
This repository only persists and retrieves deterministic initial state rows.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plant_character import PlantCharacter


class CharacterRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, character: PlantCharacter) -> PlantCharacter:
        self.session.add(character)
        await self.session.flush()
        return character

    async def get_latest_for_plant(self, plant_id: uuid.UUID) -> PlantCharacter | None:
        """Return the most recently created character row for the plant."""
        result = await self.session.execute(
            select(PlantCharacter)
            .where(PlantCharacter.plant_id == plant_id)
            .order_by(PlantCharacter.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
