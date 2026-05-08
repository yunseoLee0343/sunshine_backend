"""TICKET-001 — Repository smoke tests.

Requires a live PostgreSQL database with the schema migrated.
Skipped automatically if DATABASE_URL is not set.

The smoke tests intentionally avoid app.db.session.AsyncSessionLocal and
pytest-asyncio async-generator fixtures. Each test runs its DB lifecycle inside
one asyncio.run() call so engine creation, query execution, rollback, session
close, and engine disposal all happen on the same event loop.
"""

import asyncio
import os
from collections.abc import Awaitable, Callable
from typing import TypeVar

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

if not os.environ.get("DATABASE_URL"):
    pytest.skip(
        "DATABASE_URL not set — skipping smoke tests (requires live Postgres)",
        allow_module_level=True,
    )

from app.repositories.smoke_repository import SmokeRepository  # noqa: E402

DATABASE_URL: str = os.environ["DATABASE_URL"]
T = TypeVar("T")


async def _run_with_session(fn: Callable[[AsyncSession], Awaitable[T]]) -> T:
    """Run one smoke operation with a fully isolated async DB lifecycle.

    The repository methods flush but do not commit. Rolling back removes smoke
    rows while keeping the Alembic-created schema intact.
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

    try:
        async with session_factory() as session:
            try:
                return await fn(session)
            finally:
                if session.in_transaction():
                    await session.rollback()
    finally:
        await engine.dispose()


def test_smoke_create_user() -> None:
    async def _case(session: AsyncSession) -> None:
        repo = SmokeRepository(session)

        user = await repo.create_smoke_user()

        assert user.id is not None
        assert user.display_name == "smoke-test-user"

    asyncio.run(_run_with_session(_case))


def test_smoke_create_species() -> None:
    async def _case(session: AsyncSession) -> None:
        repo = SmokeRepository(session)

        species = await repo.create_smoke_species()

        assert species.id is not None
        assert species.korean_name == "스모크 식물"

    asyncio.run(_run_with_session(_case))


def test_smoke_create_plant_linked() -> None:
    async def _case(session: AsyncSession) -> None:
        repo = SmokeRepository(session)

        user = await repo.create_smoke_user()
        species = await repo.create_smoke_species()
        plant = await repo.create_smoke_plant(user.id, species.id)

        assert plant.id is not None
        assert plant.user_id == user.id
        assert plant.species_profile_id == species.id

    asyncio.run(_run_with_session(_case))


def test_smoke_read_plant_back() -> None:
    async def _case(session: AsyncSession) -> None:
        repo = SmokeRepository(session)

        user = await repo.create_smoke_user()
        plant = await repo.create_smoke_plant(user.id)
        fetched = await repo.get_plant(plant.id)

        assert fetched is not None
        assert fetched.id == plant.id
        assert fetched.nickname == "smoke-plant"

    asyncio.run(_run_with_session(_case))


def test_smoke_delete_rolls_back() -> None:
    async def _case(session: AsyncSession) -> None:
        repo = SmokeRepository(session)

        user = await repo.create_smoke_user()
        species = await repo.create_smoke_species()
        plant = await repo.create_smoke_plant(user.id, species.id)
        await repo.delete_smoke_data(plant, user, species)
        fetched = await repo.get_plant(plant.id)

        assert fetched is None

    asyncio.run(_run_with_session(_case))
