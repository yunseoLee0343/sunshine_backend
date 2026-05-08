"""TICKET-001 — Repository smoke tests.

Requires a live PostgreSQL database with the schema migrated.
Skipped automatically if DATABASE_URL is not set.

These tests intentionally do not import app.db.session.AsyncSessionLocal.
The production sessionmaker owns a module-level async engine, which can leak
asyncpg connections across pytest event loops. Each smoke test creates and
cleans up its own engine/sessionmaker in the same async fixture lifecycle.
"""

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

if not os.environ.get("DATABASE_URL"):
    pytest.skip(
        "DATABASE_URL not set — skipping smoke tests (requires live Postgres)",
        allow_module_level=True,
    )

from app.repositories.smoke_repository import SmokeRepository  # noqa: E402

DATABASE_URL: str = os.environ["DATABASE_URL"]


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """Provide an isolated AsyncSession for one smoke test.

    A fresh function-scoped engine plus NullPool prevents asyncpg connections
    from being reused by a different pytest event loop. The repository methods
    only flush, so rolling back after the test leaves the migrated schema intact
    while removing smoke rows.
    """
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async with session_factory() as db_session:
        try:
            yield db_session
        finally:
            if db_session.in_transaction():
                await db_session.rollback()

    await engine.dispose()


@pytest.mark.asyncio
async def test_smoke_create_user(session: AsyncSession) -> None:
    repo = SmokeRepository(session)

    user = await repo.create_smoke_user()

    assert user.id is not None
    assert user.display_name == "smoke-test-user"


@pytest.mark.asyncio
async def test_smoke_create_species(session: AsyncSession) -> None:
    repo = SmokeRepository(session)

    species = await repo.create_smoke_species()

    assert species.id is not None
    assert species.korean_name == "스모크 식물"


@pytest.mark.asyncio
async def test_smoke_create_plant_linked(session: AsyncSession) -> None:
    repo = SmokeRepository(session)

    user = await repo.create_smoke_user()
    species = await repo.create_smoke_species()
    plant = await repo.create_smoke_plant(user.id, species.id)

    assert plant.id is not None
    assert plant.user_id == user.id
    assert plant.species_profile_id == species.id


@pytest.mark.asyncio
async def test_smoke_read_plant_back(session: AsyncSession) -> None:
    repo = SmokeRepository(session)

    user = await repo.create_smoke_user()
    plant = await repo.create_smoke_plant(user.id)
    fetched = await repo.get_plant(plant.id)

    assert fetched is not None
    assert fetched.id == plant.id
    assert fetched.nickname == "smoke-plant"


@pytest.mark.asyncio
async def test_smoke_delete_rolls_back(session: AsyncSession) -> None:
    repo = SmokeRepository(session)

    user = await repo.create_smoke_user()
    species = await repo.create_smoke_species()
    plant = await repo.create_smoke_plant(user.id, species.id)
    await repo.delete_smoke_data(plant, user, species)
    fetched = await repo.get_plant(plant.id)

    assert fetched is None