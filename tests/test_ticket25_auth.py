"""TICKET-025 — Auth / User Scope unit tests (no live DB).

Verifies:
  - app/core/auth.py: CurrentUser, get_current_user, resolve_user_id
  - GET routes accept X-User-Id header in place of ?user_id= query param
  - Header user_id is passed to the service layer as the effective identity
  - Cross-user access via header is denied with 403
  - Missing both header and query param returns 422
  - POST routes use X-User-Id header when present (overrides body user_id)
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.core.auth import CurrentUser, get_current_user, resolve_user_id
from app.main import app
from app.models.plant import Plant
from app.schemas.plants import CharacterBlock, PlantCard, SpeciesBlock

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SPECIES = SpeciesBlock(
    korean_name="몬스테라", scientific_name="Monstera deliciosa", common_name="Monstera"
)
_CHARACTER = CharacterBlock(
    mood="neutral",
    expression="normal",
    status_message="새 식물이 등록되었어요.",
    primary_action="none",
    reason_code="onboarding_created",
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


def _make_card(user_id: uuid.UUID, plant_id: uuid.UUID) -> PlantCard:
    return PlantCard(
        plant_id=plant_id,
        user_id=user_id,
        species_profile_id=uuid.uuid4(),
        nickname="초록이",
        room_name="거실",
        species=_SPECIES,
        character=_CHARACTER,
    )


async def _get(
    path: str,
    params: dict | None = None,
    headers: dict | None = None,
) -> tuple[int, dict]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.get(path, params=params or {}, headers=headers or {})
    return r.status_code, r.json()


async def _post(
    path: str,
    body: dict,
    headers: dict | None = None,
) -> tuple[int, dict]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.post(path, json=body, headers=headers or {})
    return r.status_code, r.json()


# ---------------------------------------------------------------------------
# app/core/auth.py unit tests (no HTTP)
# ---------------------------------------------------------------------------


def test_get_current_user_returns_none_without_header() -> None:
    result = get_current_user(x_user_id=None)
    assert result is None


def test_get_current_user_parses_valid_uuid() -> None:
    uid = uuid.uuid4()
    result = get_current_user(x_user_id=str(uid))
    assert result is not None
    assert result.user_id == uid


def test_get_current_user_raises_422_for_invalid_uuid() -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(x_user_id="not-a-uuid")
    assert exc_info.value.status_code == 422


def test_resolve_user_id_prefers_header_over_query_param() -> None:
    header_uid = uuid.uuid4()
    query_uid = uuid.uuid4()
    result = resolve_user_id(query_uid, CurrentUser(user_id=header_uid))
    assert result == header_uid


def test_resolve_user_id_falls_back_to_query_param() -> None:
    uid = uuid.uuid4()
    result = resolve_user_id(uid, None)
    assert result == uid


def test_resolve_user_id_raises_422_when_neither() -> None:
    with pytest.raises(HTTPException) as exc_info:
        resolve_user_id(None, None)
    assert exc_info.value.status_code == 422


def test_current_user_is_frozen() -> None:
    u = CurrentUser(user_id=uuid.uuid4())
    with pytest.raises(Exception):
        u.user_id = uuid.uuid4()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# GET /plants/{plant_id} — header-based ownership
# ---------------------------------------------------------------------------

_SVC = "app.api.plants.PlantOnboardingService"


def test_get_plant_with_header_returns_200() -> None:
    owner = uuid.uuid4()
    plant_id = uuid.uuid4()
    card = _make_card(owner, plant_id)

    with patch(f"{_SVC}.get_plant", new=AsyncMock(return_value=card)):
        status, _ = asyncio.run(
            _get(f"/plants/{plant_id}", headers={"X-User-Id": str(owner)})
        )
    assert status == 200


def test_get_plant_header_user_id_is_passed_to_service() -> None:
    """Verify the header value (not a query param) is forwarded to get_plant."""
    owner = uuid.uuid4()
    plant_id = uuid.uuid4()
    card = _make_card(owner, plant_id)

    mock = AsyncMock(return_value=card)
    with patch(f"{_SVC}.get_plant", new=mock):
        asyncio.run(
            _get(f"/plants/{plant_id}", headers={"X-User-Id": str(owner)})
        )

    # call_args positional: (plant_id, user_id) — self is not captured by AsyncMock patch
    called_plant_id, called_user_id = mock.call_args[0]
    assert called_plant_id == plant_id
    assert called_user_id == owner


def test_get_plant_header_cross_user_returns_403() -> None:
    owner = uuid.uuid4()
    attacker = uuid.uuid4()
    plant_id = uuid.uuid4()
    plant = _make_plant(owner, plant_id)

    async def _ownership_aware(self_arg, p_id: uuid.UUID, u_id: uuid.UUID) -> PlantCard:
        if u_id != plant.user_id:
            raise HTTPException(status_code=403, detail="forbidden")
        return _make_card(owner, p_id)

    with patch(f"{_SVC}.get_plant", new=_ownership_aware):
        status, body = asyncio.run(
            _get(f"/plants/{plant_id}", headers={"X-User-Id": str(attacker)})
        )
    assert status == 403
    assert body["detail"] == "forbidden"


def test_get_plant_no_header_no_query_param_returns_422() -> None:
    plant_id = uuid.uuid4()
    status, _ = asyncio.run(_get(f"/plants/{plant_id}"))
    assert status == 422


def test_get_plant_header_wins_over_query_param() -> None:
    """When both header and query param are supplied, header user_id is used."""
    header_uid = uuid.uuid4()
    query_uid = uuid.uuid4()
    plant_id = uuid.uuid4()
    card = _make_card(header_uid, plant_id)

    mock = AsyncMock(return_value=card)
    with patch(f"{_SVC}.get_plant", new=mock):
        asyncio.run(
            _get(
                f"/plants/{plant_id}",
                params={"user_id": str(query_uid)},
                headers={"X-User-Id": str(header_uid)},
            )
        )

    _pid, passed_uid = mock.call_args[0]
    assert passed_uid == header_uid  # not query_uid


# ---------------------------------------------------------------------------
# GET /plants — list
# ---------------------------------------------------------------------------


def test_list_plants_with_header_returns_200() -> None:
    uid = uuid.uuid4()
    with patch(f"{_SVC}.list_plants", new=AsyncMock(return_value=[])):
        status, _ = asyncio.run(
            _get("/plants", headers={"X-User-Id": str(uid)})
        )
    assert status == 200


def test_list_plants_no_identity_returns_422() -> None:
    status, _ = asyncio.run(_get("/plants"))
    assert status == 422


# ---------------------------------------------------------------------------
# POST /plants/{plant_id}/character-state — header overrides body user_id
# ---------------------------------------------------------------------------

from app.api.plants import get_session  # noqa: E402


def _setup_session(plant: Plant | None) -> None:
    async def _fake():
        sess = MagicMock()
        sess.commit = AsyncMock()
        yield sess

    app.dependency_overrides[get_session] = _fake


def _clear() -> None:
    app.dependency_overrides.clear()


def test_character_state_header_overrides_body_user_id() -> None:
    """Header user_id takes precedence over body user_id for ownership."""
    owner = uuid.uuid4()
    attacker = uuid.uuid4()
    plant_id = uuid.uuid4()
    plant = _make_plant(owner, plant_id)

    _setup_session(plant)
    with (
        patch("app.api.plants.PlantRepository.get_by_id", new=AsyncMock(return_value=plant)),
        patch("app.api.plants.CharacterRepository.create", new=AsyncMock(side_effect=lambda c: c)),
    ):
        try:
            # body claims attacker owns the plant, but header identifies owner — 200
            status, _ = asyncio.run(
                _post(
                    f"/plants/{plant_id}/character-state",
                    {"user_id": str(attacker), "condition": "good"},
                    headers={"X-User-Id": str(owner)},
                )
            )
        finally:
            _clear()

    assert status == 200


def test_character_state_header_cross_user_returns_403() -> None:
    """Header with wrong user_id is denied even if body claims ownership."""
    owner = uuid.uuid4()
    attacker = uuid.uuid4()
    plant_id = uuid.uuid4()
    plant = _make_plant(owner, plant_id)

    _setup_session(plant)
    with (
        patch("app.api.plants.PlantRepository.get_by_id", new=AsyncMock(return_value=plant)),
        patch("app.api.plants.CharacterRepository.create", new=AsyncMock(side_effect=lambda c: c)),
    ):
        try:
            # header identifies attacker — ownership check fails → 403
            status, _ = asyncio.run(
                _post(
                    f"/plants/{plant_id}/character-state",
                    {"user_id": str(owner), "condition": "good"},
                    headers={"X-User-Id": str(attacker)},
                )
            )
        finally:
            _clear()

    assert status == 403


# ---------------------------------------------------------------------------
# GET /home — header-based identity
# ---------------------------------------------------------------------------

_HOME_SVC = "app.api.home.HomeCardService"


def test_get_home_with_header_returns_200() -> None:
    from app.schemas.home import HomeResponse

    uid = uuid.uuid4()
    resp = HomeResponse(user_id=uid, plants=[])
    with patch(f"{_HOME_SVC}.get_home", new=AsyncMock(return_value=resp)):
        status, _ = asyncio.run(_get("/home", headers={"X-User-Id": str(uid)}))
    assert status == 200


def test_get_home_no_identity_returns_422() -> None:
    status, _ = asyncio.run(_get("/home"))
    assert status == 422
