"""Smoke repository — proves DB access and table usability only.

This repository performs no business workflow orchestration.
It exists solely to verify that the schema is reachable and
basic insert/read/delete operations work end-to-end.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plant import Plant
from app.models.species_profile import SpeciesProfile
from app.models.user import User
from app.repositories.base_repository import BaseRepository


class SmokeRepository:
    """Minimal insert/read/delete operations for smoke-testing the schema."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._users = BaseRepository(User, session)
        self._species = BaseRepository(SpeciesProfile, session)
        self._plants = BaseRepository(Plant, session)

    async def create_smoke_user(self) -> User:
        now = datetime.now(UTC)
        user = User(
            id=uuid.uuid4(),
            display_name="smoke-test-user",
            created_at=now,
            updated_at=now,
        )
        return await self._users.add(user)

    async def create_smoke_species(self) -> SpeciesProfile:
        now = datetime.now(UTC)
        species = SpeciesProfile(
            id=uuid.uuid4(),
            korean_name="스모크 식물",
            metadata_json={},
            created_at=now,
            updated_at=now,
        )
        return await self._species.add(species)

    async def create_smoke_plant(
        self,
        user_id: uuid.UUID,
        species_id: uuid.UUID | None = None,
    ) -> Plant:
        now = datetime.now(UTC)
        plant = Plant(
            id=uuid.uuid4(),
            user_id=user_id,
            species_profile_id=species_id,
            nickname="smoke-plant",
            created_at=now,
            updated_at=now,
        )
        return await self._plants.add(plant)

    async def get_plant(self, plant_id: uuid.UUID) -> Plant | None:
        return await self._plants.get(plant_id)

    async def delete_smoke_data(
        self,
        plant: Plant,
        user: User,
        species: SpeciesProfile | None = None,
    ) -> None:
        await self._plants.delete(plant)
        if species:
            await self._species.delete(species)
        await self._users.delete(user)
