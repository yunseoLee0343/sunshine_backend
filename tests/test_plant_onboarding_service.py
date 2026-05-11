"""TICKET-002 — Plant Onboarding Service unit tests.

Mocks DB so no live Postgres is needed.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.species_profile import SpeciesProfile
from app.models.user import User
from app.schemas.plants import CreatePlantRequest
from app.services.plant_onboarding import (
    _INITIAL_EXPRESSION,
    _INITIAL_MOOD,
    _INITIAL_REASON_CODE,
    _INITIAL_STATUS_MESSAGE,
    PlantOnboardingService,
)


def _mock_session():
    session = AsyncMock()
    session.get = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


def _make_user() -> User:
    now = datetime.now(UTC)
    return User(id=uuid.uuid4(), display_name="tester", created_at=now, updated_at=now)


def _make_species() -> SpeciesProfile:
    now = datetime.now(UTC)
    return SpeciesProfile(
        id=uuid.uuid4(),
        korean_name="몬스테라",
        scientific_name="Monstera deliciosa",
        common_name="Monstera",
        metadata_json={},
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# create_plant
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_plant_returns_card() -> None:
    session = _mock_session()
    user = _make_user()
    species = _make_species()

    session.get.return_value = user

    svc = PlantOnboardingService(session)
    svc.species_repo.get_by_id = AsyncMock(return_value=species)
    svc.plant_repo.create = AsyncMock(side_effect=lambda p: p)
    svc.char_repo.create = AsyncMock(side_effect=lambda c: c)

    req = CreatePlantRequest(
        user_id=user.id,
        species_profile_id=species.id,
        nickname="초록이",
        room_name="거실",
    )
    card = await svc.create_plant(req)

    assert card.nickname == "초록이"
    assert card.room_name == "거실"
    assert card.user_id == user.id
    assert card.species_profile_id == species.id


@pytest.mark.asyncio
async def test_create_plant_initial_character_state() -> None:
    session = _mock_session()
    user = _make_user()
    species = _make_species()

    session.get.return_value = user
    svc = PlantOnboardingService(session)
    svc.species_repo.get_by_id = AsyncMock(return_value=species)
    svc.plant_repo.create = AsyncMock(side_effect=lambda p: p)
    svc.char_repo.create = AsyncMock(side_effect=lambda c: c)

    req = CreatePlantRequest(
        user_id=user.id,
        species_profile_id=species.id,
        nickname="초록이",
    )
    card = await svc.create_plant(req)

    assert card.character is not None
    assert card.character.mood == _INITIAL_MOOD
    assert card.character.expression == _INITIAL_EXPRESSION
    assert card.character.status_message == _INITIAL_STATUS_MESSAGE
    assert card.character.reason_code == _INITIAL_REASON_CODE


@pytest.mark.asyncio
async def test_create_plant_commits_once() -> None:
    session = _mock_session()
    user = _make_user()
    species = _make_species()

    session.get.return_value = user
    svc = PlantOnboardingService(session)
    svc.species_repo.get_by_id = AsyncMock(return_value=species)
    svc.plant_repo.create = AsyncMock(side_effect=lambda p: p)
    svc.char_repo.create = AsyncMock(side_effect=lambda c: c)

    req = CreatePlantRequest(user_id=user.id, species_profile_id=species.id, nickname="초록이")
    await svc.create_plant(req)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_plant_unknown_user_raises_404() -> None:
    from fastapi import HTTPException

    session = _mock_session()
    session.get.return_value = None  # user not found

    svc = PlantOnboardingService(session)
    req = CreatePlantRequest(user_id=uuid.uuid4(), species_profile_id=uuid.uuid4(), nickname="초록이")
    with pytest.raises(HTTPException) as exc:
        await svc.create_plant(req)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_create_plant_unknown_species_raises_404() -> None:
    from fastapi import HTTPException

    session = _mock_session()
    user = _make_user()
    session.get.return_value = user

    svc = PlantOnboardingService(session)
    svc.species_repo.get_by_id = AsyncMock(return_value=None)

    req = CreatePlantRequest(user_id=user.id, species_profile_id=uuid.uuid4(), nickname="초록이")
    with pytest.raises(HTTPException) as exc:
        await svc.create_plant(req)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_create_plant_room_name_optional() -> None:
    session = _mock_session()
    user = _make_user()
    species = _make_species()

    session.get.return_value = user
    svc = PlantOnboardingService(session)
    svc.species_repo.get_by_id = AsyncMock(return_value=species)
    svc.plant_repo.create = AsyncMock(side_effect=lambda p: p)
    svc.char_repo.create = AsyncMock(side_effect=lambda c: c)

    req = CreatePlantRequest(
        user_id=user.id,
        species_profile_id=species.id,
        nickname="초록이",
        # room_name omitted
    )
    card = await svc.create_plant(req)
    assert card.room_name is None


# ---------------------------------------------------------------------------
# Schema validation (no DB needed)
# ---------------------------------------------------------------------------


def test_create_plant_request_missing_species_rejected() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        CreatePlantRequest(user_id=uuid.uuid4(), nickname="초록이")  # type: ignore[call-arg]


def test_create_plant_request_missing_nickname_rejected() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        CreatePlantRequest(user_id=uuid.uuid4(), species_profile_id=uuid.uuid4())  # type: ignore[call-arg]


def test_create_plant_request_empty_nickname_rejected() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        CreatePlantRequest(user_id=uuid.uuid4(), species_profile_id=uuid.uuid4(), nickname="   ")
