"""SpeciesRepository — catalog lookup only.

No image classification, no model inference, no diagnosis fields.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.species_profile import SpeciesProfile


class SpeciesRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_candidates(self, limit: int = 20) -> list[SpeciesProfile]:
        """Return first N species_profiles from the DB (catalog order)."""
        result = await self.session.execute(select(SpeciesProfile).limit(limit))
        return list(result.scalars().all())

    async def get_by_id(self, species_id: uuid.UUID) -> SpeciesProfile | None:
        result = await self.session.execute(
            select(SpeciesProfile).where(SpeciesProfile.id == species_id)
        )
        return result.scalar_one_or_none()
