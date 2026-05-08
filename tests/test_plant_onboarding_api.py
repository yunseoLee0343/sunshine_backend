"""TICKET-002 — Plant Onboarding API integration tests.

Mocks the DB session / service so no live Postgres is needed.
"""

import asyncio
import uuid
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.plants import (
    CharacterBlock,
    PlantCard,
    PlantListItem,
    SpeciesBlock,
)

_SPECIES_BLOCK = SpeciesBlock(
    korean_name="몬스테라",
    scientific_name="Monstera deliciosa",
    common_name="Monstera",
)
_CHARACTER_BLOCK = CharacterBlock(
    mood="neutral",
    expression="normal",
    status_message="새 식물이 등록되었어요.",
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
        character=_CHARACTER_BLOCK,
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
# POST /plants
# ---------------------------------------------------------------------------


def test_post_plants_returns_201() -> None:
    card = _make_card()
    with patch(f"{_SVC_PATH}.create_plant", new=AsyncMock(return_value=card)):
        status, _ = asyncio.run(
            _post(
                "/plants",
                {
                    "user_id": str(uuid.uuid4()),
                    "species_profile_id": str(uuid.uuid4()),
                    "nickname": "초록이",
                    "room_name": "거실",
                },
            )
        )
    assert status == 201


def test_post_plants_response_has_plant_card() -> None:
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
    assert "plant" in body
    assert "plant_id" in body["plant"]
    assert "nickname" in body["plant"]


def test_post_plants_response_includes_species_block() -> None:
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
    assert "species" in body["plant"]
    assert body["plant"]["species"]["korean_name"] == "몬스테라"


def test_post_plants_response_includes_initial_character() -> None:
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
    assert ch["reason_code"] == "onboarding_created"


def test_post_plants_missing_species_profile_id_returns_422() -> None:
    status, _ = asyncio.run(
        _post("/plants", {"user_id": str(uuid.uuid4()), "nickname": "초록이"})
    )
    assert status == 422


def test_post_plants_empty_nickname_returns_422() -> None:
    status, _ = asyncio.run(
        _post(
            "/plants",
            {
                "user_id": str(uuid.uuid4()),
                "species_profile_id": str(uuid.uuid4()),
                "nickname": "   ",
            },
        )
    )
    assert status == 422


def test_post_plants_unknown_user_returns_404() -> None:
    from fastapi import HTTPException

    with patch(
        f"{_SVC_PATH}.create_plant",
        new=AsyncMock(side_effect=HTTPException(status_code=404, detail="user not found")),
    ):
        status, _ = asyncio.run(
            _post(
                "/plants",
                {
                    "user_id": str(uuid.uuid4()),
                    "species_profile_id": str(uuid.uuid4()),
                    "nickname": "초록이",
                },
            )
        )
    assert status == 404


def test_post_plants_unknown_species_returns_404() -> None:
    from fastapi import HTTPException

    with patch(
        f"{_SVC_PATH}.create_plant",
        new=AsyncMock(
            side_effect=HTTPException(status_code=404, detail="species_profile not found")
        ),
    ):
        status, _ = asyncio.run(
            _post(
                "/plants",
                {
                    "user_id": str(uuid.uuid4()),
                    "species_profile_id": str(uuid.uuid4()),
                    "nickname": "초록이",
                },
            )
        )
    assert status == 404


# ---------------------------------------------------------------------------
# GET /plants
# ---------------------------------------------------------------------------


def test_get_plants_returns_only_user_plants() -> None:
    user_id = uuid.uuid4()
    items = [
        PlantListItem(
            plant_id=uuid.uuid4(),
            nickname="초록이",
            room_name="거실",
            species=_SPECIES_BLOCK,
            character=_CHARACTER_BLOCK,
        )
    ]
    with patch(f"{_SVC_PATH}.list_plants", new=AsyncMock(return_value=items)):
        status, body = asyncio.run(_get("/plants", params={"user_id": str(user_id)}))
    assert status == 200
    assert "plants" in body
    assert len(body["plants"]) == 1


def test_get_plants_no_sensor_snapshot_field() -> None:
    items = [
        PlantListItem(
            plant_id=uuid.uuid4(),
            nickname="초록이",
            room_name=None,
            species=_SPECIES_BLOCK,
            character=_CHARACTER_BLOCK,
        )
    ]
    with patch(f"{_SVC_PATH}.list_plants", new=AsyncMock(return_value=items)):
        _, body = asyncio.run(_get("/plants", params={"user_id": str(uuid.uuid4())}))
    for plant in body["plants"]:
        assert "sensor_snapshot" not in plant
        assert "today_recommended_action" not in plant
        assert "chat_history" not in plant


# ---------------------------------------------------------------------------
# GET /plants/{plant_id}
# ---------------------------------------------------------------------------


def test_get_plant_detail_returns_200() -> None:
    user_id = uuid.uuid4()
    plant_id = uuid.uuid4()
    card = _make_card(user_id=user_id, plant_id=plant_id)
    with patch(f"{_SVC_PATH}.get_plant", new=AsyncMock(return_value=card)):
        status, body = asyncio.run(
            _get(f"/plants/{plant_id}", params={"user_id": str(user_id)})
        )
    assert status == 200
    assert "plant" in body


def test_get_plant_cross_user_returns_403() -> None:
    from fastapi import HTTPException

    plant_id = uuid.uuid4()
    with patch(
        f"{_SVC_PATH}.get_plant",
        new=AsyncMock(side_effect=HTTPException(status_code=403, detail="forbidden")),
    ):
        status, _ = asyncio.run(
            _get(f"/plants/{plant_id}", params={"user_id": str(uuid.uuid4())})
        )
    assert status == 403


def test_get_plant_not_found_returns_404() -> None:
    from fastapi import HTTPException

    plant_id = uuid.uuid4()
    with patch(
        f"{_SVC_PATH}.get_plant",
        new=AsyncMock(side_effect=HTTPException(status_code=404, detail="not found")),
    ):
        status, _ = asyncio.run(
            _get(f"/plants/{plant_id}", params={"user_id": str(uuid.uuid4())})
        )
    assert status == 404
