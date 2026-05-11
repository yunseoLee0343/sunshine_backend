"""TICKET-002 — Plant Onboarding DB integration tests.

These tests use a live PostgreSQL database and real API/service/repository code.
They are skipped automatically when DATABASE_URL is not set.

Precondition:
    alembic upgrade head
"""

import os
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

if not os.environ.get("DATABASE_URL"):
    pytest.skip(
        "DATABASE_URL not set — skipping DB integration tests",
        allow_module_level=True,
    )

from app.api.plants import get_session
from app.main import app
from app.models.plant import Plant
from app.models.plant_character import PlantCharacter
from app.models.species_profile import SpeciesProfile
from app.models.user import User

DATABASE_URL = os.environ["DATABASE_URL"]

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Provide a real AsyncSession backed by live PostgreSQL.

    NullPool prevents asyncpg connections from leaking across pytest event loops.
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

    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """FastAPI test client using the real app but overridden DB session.

    The router/service/repository stack remains real.
    Only the session dependency is overridden so the test can clean up rows.
    """

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        try:
            yield ac
        finally:
            app.dependency_overrides.clear()


async def _seed_user(
    session: AsyncSession,
    *,
    display_name: str = "db-integration-user",
) -> User:
    now = datetime.now(UTC)
    user = User(
        id=uuid.uuid4(),
        display_name=display_name,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    await session.commit()
    return user


async def _seed_species(
    session: AsyncSession,
    *,
    korean_name: str = "통합테스트 식물",
    scientific_name: str = "Integration test species",
    common_name: str = "Integration Plant",
) -> SpeciesProfile:
    now = datetime.now(UTC)
    species = SpeciesProfile(
        id=uuid.uuid4(),
        korean_name=korean_name,
        scientific_name=scientific_name,
        common_name=common_name,
        metadata_json={},
        created_at=now,
        updated_at=now,
    )
    session.add(species)
    await session.commit()
    return species


async def _cleanup_test_rows(
    session: AsyncSession,
    *,
    user_ids: list[uuid.UUID] | None = None,
    species_ids: list[uuid.UUID] | None = None,
) -> None:
    """Delete rows created by this test in FK-safe order."""
    user_ids = user_ids or []
    species_ids = species_ids or []

    await session.rollback()

    plant_ids: list[uuid.UUID] = []
    if user_ids:
        result = await session.execute(select(Plant.id).where(Plant.user_id.in_(user_ids)))
        plant_ids = list(result.scalars().all())

    if plant_ids:
        await session.execute(delete(PlantCharacter).where(PlantCharacter.plant_id.in_(plant_ids)))
        await session.execute(delete(Plant).where(Plant.id.in_(plant_ids)))

    if species_ids:
        await session.execute(delete(SpeciesProfile).where(SpeciesProfile.id.in_(species_ids)))

    if user_ids:
        await session.execute(delete(User).where(User.id.in_(user_ids)))

    await session.commit()


async def test_post_plants_persists_plant_and_initial_character(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await _seed_user(db_session)
    species = await _seed_species(db_session)

    try:
        response = await client.post(
            "/plants",
            json={
                "user_id": str(user.id),
                "species_profile_id": str(species.id),
                "nickname": "초록이",
                "room_name": "거실",
            },
        )

        assert response.status_code == 201
        body = response.json()

        plant = body["plant"]
        plant_id = uuid.UUID(plant["plant_id"])

        assert plant["user_id"] == str(user.id)
        assert plant["species_profile_id"] == str(species.id)
        assert plant["nickname"] == "초록이"
        assert plant["room_name"] == "거실"

        assert plant["species"] == {
            "korean_name": "통합테스트 식물",
            "scientific_name": "Integration test species",
            "common_name": "Integration Plant",
        }

        assert plant["character"] == {
            "mood": "neutral",
            "expression": "normal",
            "status_message": "새 식물이 등록되었어요.",
            "reason_code": "onboarding_created",
        }

        persisted_plant = await db_session.get(Plant, plant_id)
        assert persisted_plant is not None
        assert persisted_plant.user_id == user.id
        assert persisted_plant.species_profile_id == species.id
        assert persisted_plant.nickname == "초록이"
        assert persisted_plant.room_name == "거실"

        result = await db_session.execute(select(PlantCharacter).where(PlantCharacter.plant_id == plant_id))
        persisted_character = result.scalar_one_or_none()

        assert persisted_character is not None
        assert persisted_character.mood == "neutral"
        assert persisted_character.expression == "normal"
        assert persisted_character.status_message == "새 식물이 등록되었어요."
        assert persisted_character.reason_code == "onboarding_created"

    finally:
        await _cleanup_test_rows(
            db_session,
            user_ids=[user.id],
            species_ids=[species.id],
        )


async def test_get_plants_lists_only_requested_users_plants(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user_a = await _seed_user(db_session, display_name="user-a")
    user_b = await _seed_user(db_session, display_name="user-b")
    species = await _seed_species(db_session)

    try:
        response_a = await client.post(
            "/plants",
            json={
                "user_id": str(user_a.id),
                "species_profile_id": str(species.id),
                "nickname": "유저A식물",
            },
        )
        assert response_a.status_code == 201

        response_b = await client.post(
            "/plants",
            json={
                "user_id": str(user_b.id),
                "species_profile_id": str(species.id),
                "nickname": "유저B식물",
            },
        )
        assert response_b.status_code == 201

        list_response = await client.get(
            "/plants",
            params={"user_id": str(user_a.id)},
        )

        assert list_response.status_code == 200
        body = list_response.json()

        assert "plants" in body
        nicknames = {item["nickname"] for item in body["plants"]}

        assert "유저A식물" in nicknames
        assert "유저B식물" not in nicknames

        for item in body["plants"]:
            assert "sensor_snapshot" not in item
            assert "today_recommended_action" not in item
            assert "chat_history" not in item

    finally:
        await _cleanup_test_rows(
            db_session,
            user_ids=[user_a.id, user_b.id],
            species_ids=[species.id],
        )


async def test_get_plant_detail_enforces_user_ownership(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    owner = await _seed_user(db_session, display_name="owner")
    other_user = await _seed_user(db_session, display_name="other")
    species = await _seed_species(db_session)

    try:
        create_response = await client.post(
            "/plants",
            json={
                "user_id": str(owner.id),
                "species_profile_id": str(species.id),
                "nickname": "소유자식물",
                "room_name": "방",
            },
        )
        assert create_response.status_code == 201

        plant_id = create_response.json()["plant"]["plant_id"]

        owner_response = await client.get(
            f"/plants/{plant_id}",
            params={"user_id": str(owner.id)},
        )

        assert owner_response.status_code == 200
        owner_body = owner_response.json()
        assert owner_body["plant"]["plant_id"] == plant_id
        assert owner_body["plant"]["user_id"] == str(owner.id)
        assert owner_body["plant"]["nickname"] == "소유자식물"

        cross_user_response = await client.get(
            f"/plants/{plant_id}",
            params={"user_id": str(other_user.id)},
        )

        assert cross_user_response.status_code == 403

    finally:
        await _cleanup_test_rows(
            db_session,
            user_ids=[owner.id, other_user.id],
            species_ids=[species.id],
        )


async def test_get_plant_detail_unknown_plant_returns_404(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await _seed_user(db_session)

    try:
        response = await client.get(
            f"/plants/{uuid.uuid4()}",
            params={"user_id": str(user.id)},
        )

        assert response.status_code == 404

    finally:
        await _cleanup_test_rows(db_session, user_ids=[user.id])


async def test_species_candidates_reads_species_catalog_from_db(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    species_a = await _seed_species(
        db_session,
        korean_name="통합 후보 A",
        scientific_name="Candidate A",
        common_name="CandidateA",
    )
    species_b = await _seed_species(
        db_session,
        korean_name="통합 후보 B",
        scientific_name="Candidate B",
        common_name="CandidateB",
    )
    user = await _seed_user(db_session)

    try:
        response = await client.post(
            "/plants/species-candidates",
            json={
                "user_id": str(user.id),
                "image_ref": "uploads/mock/image.jpg",
            },
        )

        assert response.status_code == 200
        body = response.json()

        assert "candidates" in body

        candidates_by_id = {uuid.UUID(item["species_profile_id"]): item for item in body["candidates"]}

        assert species_a.id in candidates_by_id
        assert species_b.id in candidates_by_id

        item_a = candidates_by_id[species_a.id]
        assert item_a["korean_name"] == "통합 후보 A"
        assert item_a["scientific_name"] == "Candidate A"
        assert item_a["common_name"] == "CandidateA"
        assert item_a["confidence_label"] == "mock_or_catalog_match"

        for item in body["candidates"]:
            forbidden = {
                "disease",
                "pest",
                "health",
                "diagnosis",
                "confidence_score",
            }
            assert not forbidden.intersection(item.keys())

    finally:
        await _cleanup_test_rows(
            db_session,
            user_ids=[user.id],
            species_ids=[species_a.id, species_b.id],
        )
