"""TICKET-004 — Character state API integration tests.

Covers:
  - plant onboarding response includes the deterministic initial character
  - plant detail/list response include the latest character block
  - POST /plants/{plant_id}/character-state appends a deterministic state
  - free-form mood/expression/status_message in the request is rejected
"""

import asyncio
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient

from app.api.plants import get_session
from app.main import app
from app.models.plant import Plant
from app.schemas.plants import (
    CharacterBlock,
    PlantCard,
    SpeciesBlock,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_SPECIES_BLOCK = SpeciesBlock(
    korean_name="몬스테라",
    scientific_name="Monstera deliciosa",
    common_name="Monstera",
)
_INITIAL_CHARACTER = CharacterBlock(
    mood="neutral",
    expression="normal",
    status_message="새 식물이 등록되었어요.",
    primary_action="none",
    reason_code="onboarding_created",
)


def _make_card(
    user_id: uuid.UUID | None = None,
    plant_id: uuid.UUID | None = None,
) -> PlantCard:
    return PlantCard(
        plant_id=plant_id or uuid.uuid4(),
        user_id=user_id or uuid.uuid4(),
        species_profile_id=uuid.uuid4(),
        nickname="초록이",
        room_name="거실",
        species=_SPECIES_BLOCK,
        character=_INITIAL_CHARACTER,
    )


async def _post(path: str, body: dict) -> tuple[int, dict]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post(path, json=body)
    return r.status_code, r.json()


async def _get(path: str, params: dict | None = None) -> tuple[int, dict]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get(path, params=params)
    return r.status_code, r.json()


_SVC_PATH = "app.api.plants.PlantOnboardingService"


# ---------------------------------------------------------------------------
# Onboarding — initial character block
# ---------------------------------------------------------------------------


def test_post_plants_returns_onboarding_created_character() -> None:
    card = _make_card()
    with patch(f"{_SVC_PATH}.create_plant", new=AsyncMock(return_value=card)):
        _, body = asyncio.run(
            _post(
                "/plants",
                {
                    "user_id": str(uuid.uuid4()),
                    "species_profile_id": str(uuid.uuid4()),
                    "nickname": "초록이",
                },
            )
        )
    ch = body["plant"]["character"]
    assert ch["mood"] == "neutral"
    assert ch["expression"] == "normal"
    assert ch["status_message"] == "새 식물이 등록되었어요."
    assert ch["primary_action"] == "none"
    assert ch["reason_code"] == "onboarding_created"


def test_get_plant_detail_includes_latest_character_block() -> None:
    user_id = uuid.uuid4()
    plant_id = uuid.uuid4()
    card = PlantCard(
        plant_id=plant_id,
        user_id=user_id,
        species_profile_id=uuid.uuid4(),
        nickname="초록이",
        room_name="거실",
        species=_SPECIES_BLOCK,
        character=CharacterBlock(
            mood="thirsty",
            expression="droop",
            status_message="목이 말라 보여요.",
            primary_action="water",
            reason_code="low_soil_moisture",
        ),
    )
    with patch(f"{_SVC_PATH}.get_plant", new=AsyncMock(return_value=card)):
        status, body = asyncio.run(
            _get(f"/plants/{plant_id}", params={"user_id": str(user_id)})
        )
    assert status == 200
    ch = body["plant"]["character"]
    assert ch["mood"] == "thirsty"
    assert ch["primary_action"] == "water"
    assert ch["reason_code"] == "low_soil_moisture"


# ---------------------------------------------------------------------------
# POST /plants/{plant_id}/character-state — deterministic update
# ---------------------------------------------------------------------------


def _setup_session_override(plant: Plant | None) -> None:
    async def _fake_session_dep():
        sess = MagicMock()
        sess.commit = AsyncMock()
        yield sess

    app.dependency_overrides[get_session] = _fake_session_dep


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def _patch_repos(plant: Plant | None):
    return (
        patch(
            "app.api.plants.PlantRepository.get_by_id",
            new=AsyncMock(return_value=plant),
        ),
        patch(
            "app.api.plants.CharacterRepository.create",
            new=AsyncMock(side_effect=lambda c: c),
        ),
    )


def _make_plant(user_id: uuid.UUID, plant_id: uuid.UUID) -> Plant:
    now = datetime.now(UTC)
    return Plant(
        id=plant_id,
        user_id=user_id,
        species_profile_id=uuid.uuid4(),
        nickname="초록이",
        room_name="거실",
        created_at=now,
        updated_at=now,
    )


def test_character_state_update_deterministic() -> None:
    user_id = uuid.uuid4()
    plant_id = uuid.uuid4()
    plant = _make_plant(user_id, plant_id)

    _setup_session_override(plant)
    p1, p2 = _patch_repos(plant)
    try:
        with p1, p2:
            status, body = asyncio.run(
                _post(
                    f"/plants/{plant_id}/character-state",
                    {"user_id": str(user_id), "condition": "low_soil_moisture"},
                )
            )
    finally:
        _clear_overrides()

    assert status == 200
    ch = body["character"]
    assert ch["mood"] == "thirsty"
    assert ch["expression"] == "droop"
    assert ch["primary_action"] == "water"
    assert ch["reason_code"] == "low_soil_moisture"
    assert ch["status_message"] == "목이 말라 보여요."


def test_character_state_update_rejects_freeform_fields() -> None:
    user_id = uuid.uuid4()
    plant_id = uuid.uuid4()
    plant = _make_plant(user_id, plant_id)

    _setup_session_override(plant)
    p1, p2 = _patch_repos(plant)
    try:
        with p1, p2:
            status, _ = asyncio.run(
                _post(
                    f"/plants/{plant_id}/character-state",
                    {
                        "user_id": str(user_id),
                        "condition": "low_soil_moisture",
                        # Forbidden direct injection — must 422.
                        "mood": "whatever",
                        "expression": "sparkle",
                        "status_message": "made up by client",
                    },
                )
            )
    finally:
        _clear_overrides()

    assert status == 422


def test_character_state_update_rejects_unknown_condition() -> None:
    user_id = uuid.uuid4()
    plant_id = uuid.uuid4()
    plant = _make_plant(user_id, plant_id)

    _setup_session_override(plant)
    p1, p2 = _patch_repos(plant)
    try:
        with p1, p2:
            status, _ = asyncio.run(
                _post(
                    f"/plants/{plant_id}/character-state",
                    {
                        "user_id": str(user_id),
                        "condition": "make_it_super_cute_by_llm",
                    },
                )
            )
    finally:
        _clear_overrides()

    # Pydantic Literal mismatch yields 422 before the engine is even called.
    assert status == 422


def test_character_state_update_cross_user_returns_403() -> None:
    plant_owner = uuid.uuid4()
    other_user = uuid.uuid4()
    plant_id = uuid.uuid4()
    plant = _make_plant(plant_owner, plant_id)

    _setup_session_override(plant)
    p1, p2 = _patch_repos(plant)
    try:
        with p1, p2:
            status, _ = asyncio.run(
                _post(
                    f"/plants/{plant_id}/character-state",
                    {"user_id": str(other_user), "condition": "good"},
                )
            )
    finally:
        _clear_overrides()

    assert status == 403


def test_character_state_update_unknown_plant_returns_404() -> None:
    user_id = uuid.uuid4()
    plant_id = uuid.uuid4()

    _setup_session_override(None)
    p1, p2 = _patch_repos(None)
    try:
        with p1, p2:
            status, _ = asyncio.run(
                _post(
                    f"/plants/{plant_id}/character-state",
                    {"user_id": str(user_id), "condition": "good"},
                )
            )
    finally:
        _clear_overrides()

    assert status == 404


def test_character_state_update_persists_via_repository() -> None:
    """Each request must call CharacterRepository.create exactly once."""
    user_id = uuid.uuid4()
    plant_id = uuid.uuid4()
    plant = _make_plant(user_id, plant_id)

    _setup_session_override(plant)
    create_mock = AsyncMock(side_effect=lambda c: c)
    with (
        patch(
            "app.api.plants.PlantRepository.get_by_id",
            new=AsyncMock(return_value=plant),
        ),
        patch("app.api.plants.CharacterRepository.create", new=create_mock),
    ):
        try:
            asyncio.run(
                _post(
                    f"/plants/{plant_id}/character-state",
                    {"user_id": str(user_id), "condition": "good"},
                )
            )
            asyncio.run(
                _post(
                    f"/plants/{plant_id}/character-state",
                    {"user_id": str(user_id), "condition": "after_watering"},
                )
            )
        finally:
            _clear_overrides()

    # Two requests => two appended rows (append-only, never overwrite).
    assert create_mock.await_count == 2
