"""TICKET-024 — MVP end-to-end flow tests.

Validates the 12-step demo scenario through the live HTTP API.
Skipped automatically when DATABASE_URL is not set.

Covered flows:
  1-4   : Home card, plant list, plant detail (demo data present)
  5-7   : Companion recommendations (count, exclusions, compatibility scores)
  8-9   : Chat — watering question (intent routing, 4-section answer)
  10-11 : Chat — pest question (reference-only flag, disclaimer in [주의])
  12    : Chat — companion question (companion_plant_question intent)
  13    : Chat idempotency (duplicate request_id returns from_cache=True)
  14    : Audit evidence API (/chat-runs/{request_id}/evidence)
  15    : Auth guard on companion endpoint (wrong user → 403)
"""

from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.seeds.demo_seed import (
    DEMO_MONSTERA_SPECIES_ID,
    DEMO_PLANT_ID,
    DEMO_USER_ID,
)

if not os.environ.get("DATABASE_URL"):
    pytest.skip(
        "DATABASE_URL not set — skipping E2E tests",
        allow_module_level=True,
    )

pytestmark = pytest.mark.e2e

# Fixed request IDs — deterministic, safe to clean up by plant_id
_WATERING_REQUEST_ID = uuid.UUID("00000000-0000-0000-0024-000000000001")
_PEST_REQUEST_ID = uuid.UUID("00000000-0000-0000-0024-000000000002")
_COMPANION_CHAT_ID = uuid.UUID("00000000-0000-0000-0024-000000000003")
_IDEMPOTENCY_ID = uuid.UUID("00000000-0000-0000-0024-000000000004")


# ---------------------------------------------------------------------------
# Module-scoped response fixtures (one API call per fixture, shared across tests)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module")
async def home_resp(client: AsyncClient) -> dict:
    r = await client.get("/home", params={"user_id": str(DEMO_USER_ID)})
    assert r.status_code == 200, r.text
    return r.json()


@pytest_asyncio.fixture(scope="module")
async def plant_card_resp(client: AsyncClient) -> dict:
    r = await client.get(
        f"/plants/{DEMO_PLANT_ID}/card",
        params={"user_id": str(DEMO_USER_ID)},
    )
    assert r.status_code == 200, r.text
    return r.json()


@pytest_asyncio.fixture(scope="module")
async def list_plants_resp(client: AsyncClient) -> dict:
    r = await client.get("/plants", params={"user_id": str(DEMO_USER_ID)})
    assert r.status_code == 200, r.text
    return r.json()


@pytest_asyncio.fixture(scope="module")
async def get_plant_resp(client: AsyncClient) -> dict:
    r = await client.get(
        f"/plants/{DEMO_PLANT_ID}",
        params={"user_id": str(DEMO_USER_ID)},
    )
    assert r.status_code == 200, r.text
    return r.json()


@pytest_asyncio.fixture(scope="module")
async def companion_resp(client: AsyncClient) -> dict:
    r = await client.get(
        f"/plants/{DEMO_PLANT_ID}/companion-recommendations",
        params={"user_id": str(DEMO_USER_ID)},
    )
    assert r.status_code == 200, r.text
    return r.json()


@pytest_asyncio.fixture(scope="module")
async def watering_resp(client: AsyncClient) -> dict:
    r = await client.post(
        f"/plants/{DEMO_PLANT_ID}/chat",
        json={
            "request_id": str(_WATERING_REQUEST_ID),
            "user_id": str(DEMO_USER_ID),
            "question": "물 주는 시기가 언제야?",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest_asyncio.fixture(scope="module")
async def pest_resp(client: AsyncClient) -> dict:
    r = await client.post(
        f"/plants/{DEMO_PLANT_ID}/chat",
        json={
            "request_id": str(_PEST_REQUEST_ID),
            "user_id": str(DEMO_USER_ID),
            "question": "잎이 노랗게 변하고 있어요. 병인가요?",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest_asyncio.fixture(scope="module")
async def companion_chat_resp(client: AsyncClient) -> dict:
    r = await client.post(
        f"/plants/{DEMO_PLANT_ID}/chat",
        json={
            "request_id": str(_COMPANION_CHAT_ID),
            "user_id": str(DEMO_USER_ID),
            "question": "몬스테라랑 같이 키울 수 있는 식물 추천해줘",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------------------
# 1-4: Plant presence and home card
# ---------------------------------------------------------------------------


def test_home_has_demo_plant(home_resp: dict) -> None:
    plant_ids = [p["plant_id"] for p in home_resp.get("plants", [])]
    assert str(DEMO_PLANT_ID) in plant_ids


def test_plant_card_primary_action_is_water(plant_card_resp: dict) -> None:
    assert plant_card_resp["character"]["primary_action"] == "water"


def test_list_plants_includes_demo_plant(list_plants_resp: dict) -> None:
    plant_ids = [p["plant_id"] for p in list_plants_resp.get("plants", [])]
    assert str(DEMO_PLANT_ID) in plant_ids


def test_get_plant_nickname_is_초록이(get_plant_resp: dict) -> None:
    assert get_plant_resp["plant"]["nickname"] == "초록이"


# ---------------------------------------------------------------------------
# 5-7: Companion recommendations
# ---------------------------------------------------------------------------


def test_companion_recommendations_returns_two_candidates(companion_resp: dict) -> None:
    # Pothos and Philodendron: all 3 dimensions (light, humidity, temp) in range
    # Spathiphyllum excluded (light_max=1000 < env=1200)
    # Sansevieria excluded (humidity_max=50 < env=58)
    assert len(companion_resp["recommendations"]) == 2


def test_companion_excludes_own_species(companion_resp: dict) -> None:
    species_ids = [r["species_id"] for r in companion_resp["recommendations"]]
    assert str(DEMO_MONSTERA_SPECIES_ID) not in species_ids


def test_companion_all_candidates_fully_compatible(companion_resp: dict) -> None:
    for item in companion_resp["recommendations"]:
        assert item["compatibility_score"] == 1.0, (
            f"Expected score 1.0 for {item['common_name']}, got {item['compatibility_score']}"
        )


# ---------------------------------------------------------------------------
# 8-9: Chat watering question
# ---------------------------------------------------------------------------


def test_chat_watering_intent_classified(watering_resp: dict) -> None:
    assert watering_resp["intent"] == "watering_question"


def test_chat_watering_all_four_sections_nonempty(watering_resp: dict) -> None:
    answer = watering_resp["answer"]
    assert answer["결론"], "결론 is empty"
    assert answer["근거"], "근거 is empty"
    assert answer["행동"], "행동 is empty"
    assert answer["주의"], "주의 is empty"


# ---------------------------------------------------------------------------
# 10-11: Chat pest question (guardrail)
# ---------------------------------------------------------------------------


def test_chat_pest_is_reference_only(pest_resp: dict) -> None:
    assert pest_resp["is_reference_only"] is True


def test_chat_pest_주의_contains_disclaimer(pest_resp: dict) -> None:
    assert "참고용 지식" in pest_resp["answer"]["주의"]


# ---------------------------------------------------------------------------
# 12: Chat companion question
# ---------------------------------------------------------------------------


def test_chat_companion_intent_classified(companion_chat_resp: dict) -> None:
    assert companion_chat_resp["intent"] == "companion_plant_question"


# ---------------------------------------------------------------------------
# 13: Idempotency
# ---------------------------------------------------------------------------


async def test_chat_idempotent_returns_from_cache(client: AsyncClient) -> None:
    payload = {
        "request_id": str(_IDEMPOTENCY_ID),
        "user_id": str(DEMO_USER_ID),
        "question": "물 주는 시기가 언제야?",
    }
    await client.post(f"/plants/{DEMO_PLANT_ID}/chat", json=payload)
    r2 = await client.post(f"/plants/{DEMO_PLANT_ID}/chat", json=payload)
    assert r2.status_code == 201
    assert r2.json()["from_cache"] is True


# ---------------------------------------------------------------------------
# 14: Audit evidence
# ---------------------------------------------------------------------------


async def test_audit_evidence_returns_200_and_matches_request_id(
    client: AsyncClient, watering_resp: dict
) -> None:
    request_id = watering_resp["request_id"]
    r = await client.get(f"/chat-runs/{request_id}/evidence")
    assert r.status_code == 200
    assert r.json()["request_id"] == request_id


# ---------------------------------------------------------------------------
# 15: Auth guard
# ---------------------------------------------------------------------------


async def test_companion_wrong_user_returns_403(client: AsyncClient) -> None:
    r = await client.get(
        f"/plants/{DEMO_PLANT_ID}/companion-recommendations",
        params={"user_id": str(uuid.uuid4())},
    )
    assert r.status_code == 403
