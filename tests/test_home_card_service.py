"""TICKET-009 — HomeCardService unit tests (no DB)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.plant import Plant
from app.models.plant_character import PlantCharacter
from app.rules.schemas import RuleEngineResult
from app.schemas.home import CharacterSummary, EnvironmentBlock, PlantHomeCard

_NOW = datetime(2026, 5, 10, 12, 0, 0, tzinfo=UTC)
_USER = uuid.uuid4()
_PLANT_ID = uuid.uuid4()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_plant(plant_id: uuid.UUID = _PLANT_ID, species_profile_id: uuid.UUID | None = None) -> Plant:
    p = MagicMock(spec=Plant)
    p.id = plant_id
    p.user_id = _USER
    p.nickname = "테스트 식물"
    p.room_name = "거실"
    p.species_profile_id = species_profile_id
    return p


def _make_char(mood: str = "happy") -> PlantCharacter:
    c = MagicMock(spec=PlantCharacter)
    c.mood = mood
    c.expression = "smile"
    c.status_message = "좋아요"
    c.primary_action = "none"
    c.reason_code = "good"
    return c


def _make_rule_result(
    care_status: str = "good",
    primary_action: str = "none",
) -> RuleEngineResult:
    return RuleEngineResult(
        plant_id=_PLANT_ID,
        evaluated_at=_NOW,
        care_status=care_status,  # type: ignore[arg-type]
        primary_action=primary_action,  # type: ignore[arg-type]
        severity="none",
        reason_codes=[],
        evidence_facts={},
        rule_results=[],
    )


# ---------------------------------------------------------------------------
# _build_card: character fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_card_uses_default_character_when_none() -> None:
    """When no character row exists, neutral defaults are used (no DB write)."""
    from app.services.home_card_service import HomeCardService

    session = AsyncMock()
    svc = HomeCardService(session, now=_NOW)

    plant = _make_plant()

    svc._home_repo = AsyncMock()
    svc._home_repo.get_species_profile = AsyncMock(return_value=None)
    svc._home_repo.get_latest_character = AsyncMock(return_value=None)

    svc._rule_repo = AsyncMock()
    svc._rule_repo.get_thresholds = AsyncMock(return_value=None)
    svc._rule_repo.get_recent_care_logs = AsyncMock(return_value=[])
    svc._rule_repo.get_latest_snapshot = AsyncMock(return_value=None)

    with patch("app.services.home_card_service._ENGINE") as mock_engine:
        mock_engine.evaluate.return_value = _make_rule_result()
        card = await svc._build_card(plant)

    assert card.character.mood == "neutral"
    assert card.character.reason_code == "onboarding_created"
    # Confirm no write happened
    session.add.assert_not_called()
    session.flush.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_build_card_uses_db_character_when_present() -> None:
    from app.services.home_card_service import HomeCardService

    session = AsyncMock()
    svc = HomeCardService(session, now=_NOW)
    plant = _make_plant()
    char = _make_char(mood="thirsty")

    svc._home_repo = AsyncMock()
    svc._home_repo.get_species_profile = AsyncMock(return_value=None)
    svc._home_repo.get_latest_character = AsyncMock(return_value=char)

    svc._rule_repo = AsyncMock()
    svc._rule_repo.get_thresholds = AsyncMock(return_value=None)
    svc._rule_repo.get_recent_care_logs = AsyncMock(return_value=[])
    svc._rule_repo.get_latest_snapshot = AsyncMock(return_value=None)

    with patch("app.services.home_card_service._ENGINE") as mock_engine:
        mock_engine.evaluate.return_value = _make_rule_result()
        card = await svc._build_card(plant)

    assert card.character.mood == "thirsty"


# ---------------------------------------------------------------------------
# _build_card: environment block
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_card_environment_null_when_no_snapshot() -> None:
    from app.services.home_card_service import HomeCardService

    session = AsyncMock()
    svc = HomeCardService(session, now=_NOW)
    plant = _make_plant()

    svc._home_repo = AsyncMock()
    svc._home_repo.get_species_profile = AsyncMock(return_value=None)
    svc._home_repo.get_latest_character = AsyncMock(return_value=None)
    svc._rule_repo = AsyncMock()
    svc._rule_repo.get_thresholds = AsyncMock(return_value=None)
    svc._rule_repo.get_recent_care_logs = AsyncMock(return_value=[])
    svc._rule_repo.get_latest_snapshot = AsyncMock(return_value=None)

    with patch("app.services.home_card_service._ENGINE") as mock_engine:
        mock_engine.evaluate.return_value = _make_rule_result()
        card = await svc._build_card(plant)

    assert card.environment is None


@pytest.mark.asyncio
async def test_build_card_environment_populated_from_snapshot() -> None:
    from app.rules.types import LatestSnapshot
    from app.services.home_card_service import HomeCardService

    session = AsyncMock()
    svc = HomeCardService(session, now=_NOW)
    plant = _make_plant()

    snap = LatestSnapshot(
        soil_moisture_avg_pct=45.0,
        light_avg_lux=3000.0,
        humidity_avg_pct=55.0,
        temperature_avg_c=21.0,
    )

    svc._home_repo = AsyncMock()
    svc._home_repo.get_species_profile = AsyncMock(return_value=None)
    svc._home_repo.get_latest_character = AsyncMock(return_value=None)
    svc._rule_repo = AsyncMock()
    svc._rule_repo.get_thresholds = AsyncMock(return_value=None)
    svc._rule_repo.get_recent_care_logs = AsyncMock(return_value=[])
    svc._rule_repo.get_latest_snapshot = AsyncMock(return_value=snap)

    with patch("app.services.home_card_service._ENGINE") as mock_engine:
        mock_engine.evaluate.return_value = _make_rule_result()
        card = await svc._build_card(plant)

    assert card.environment is not None
    assert card.environment.soil_moisture_avg_pct == 45.0
    assert card.environment.temperature_avg_c == 21.0


# ---------------------------------------------------------------------------
# _build_card: rule engine
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_card_rule_engine_always_called() -> None:
    """RuleEngine.evaluate must be invoked regardless of data availability."""
    from app.services.home_card_service import HomeCardService

    session = AsyncMock()
    svc = HomeCardService(session, now=_NOW)
    plant = _make_plant()

    svc._home_repo = AsyncMock()
    svc._home_repo.get_species_profile = AsyncMock(return_value=None)
    svc._home_repo.get_latest_character = AsyncMock(return_value=None)
    svc._rule_repo = AsyncMock()
    svc._rule_repo.get_thresholds = AsyncMock(return_value=None)
    svc._rule_repo.get_recent_care_logs = AsyncMock(return_value=[])
    svc._rule_repo.get_latest_snapshot = AsyncMock(return_value=None)

    with patch("app.services.home_card_service._ENGINE") as mock_engine:
        mock_engine.evaluate.return_value = _make_rule_result(
            care_status="needs_action", primary_action="water"
        )
        card = await svc._build_card(plant)
        mock_engine.evaluate.assert_called_once()

    assert card.today_recommended_action == "water"
    assert card.care_status == "needs_action"


@pytest.mark.asyncio
async def test_build_card_rule_engine_action_not_derived_from_character() -> None:
    """today_recommended_action must come from RuleEngine, not from character."""
    from app.services.home_card_service import HomeCardService

    session = AsyncMock()
    svc = HomeCardService(session, now=_NOW)
    plant = _make_plant()
    char = _make_char(mood="happy")
    char.primary_action = "none"

    svc._home_repo = AsyncMock()
    svc._home_repo.get_species_profile = AsyncMock(return_value=None)
    svc._home_repo.get_latest_character = AsyncMock(return_value=char)
    svc._rule_repo = AsyncMock()
    svc._rule_repo.get_thresholds = AsyncMock(return_value=None)
    svc._rule_repo.get_recent_care_logs = AsyncMock(return_value=[])
    svc._rule_repo.get_latest_snapshot = AsyncMock(return_value=None)

    with patch("app.services.home_card_service._ENGINE") as mock_engine:
        mock_engine.evaluate.return_value = _make_rule_result(primary_action="water")
        card = await svc._build_card(plant)

    assert card.today_recommended_action == "water"
    assert card.character.primary_action == "none"


# ---------------------------------------------------------------------------
# _build_card: species name
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_card_species_name_from_profile() -> None:
    from app.services.home_card_service import HomeCardService

    session = AsyncMock()
    svc = HomeCardService(session, now=_NOW)
    sp_id = uuid.uuid4()
    plant = _make_plant(species_profile_id=sp_id)

    sp = MagicMock()
    sp.korean_name = "몬스테라"

    svc._home_repo = AsyncMock()
    svc._home_repo.get_species_profile = AsyncMock(return_value=sp)
    svc._home_repo.get_latest_character = AsyncMock(return_value=None)
    svc._rule_repo = AsyncMock()
    svc._rule_repo.get_thresholds = AsyncMock(return_value=None)
    svc._rule_repo.get_recent_care_logs = AsyncMock(return_value=[])
    svc._rule_repo.get_latest_snapshot = AsyncMock(return_value=None)

    with patch("app.services.home_card_service._ENGINE") as mock_engine:
        mock_engine.evaluate.return_value = _make_rule_result()
        card = await svc._build_card(plant)

    assert card.species_name == "몬스테라"


@pytest.mark.asyncio
async def test_build_card_species_name_none_when_no_profile() -> None:
    from app.services.home_card_service import HomeCardService

    session = AsyncMock()
    svc = HomeCardService(session, now=_NOW)
    plant = _make_plant(species_profile_id=None)

    svc._home_repo = AsyncMock()
    svc._home_repo.get_species_profile = AsyncMock(return_value=None)
    svc._home_repo.get_latest_character = AsyncMock(return_value=None)
    svc._rule_repo = AsyncMock()
    svc._rule_repo.get_thresholds = AsyncMock(return_value=None)
    svc._rule_repo.get_recent_care_logs = AsyncMock(return_value=[])
    svc._rule_repo.get_latest_snapshot = AsyncMock(return_value=None)

    with patch("app.services.home_card_service._ENGINE") as mock_engine:
        mock_engine.evaluate.return_value = _make_rule_result()
        card = await svc._build_card(plant)

    assert card.species_name is None


# ---------------------------------------------------------------------------
# get_plant_card: authorization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_plant_card_returns_none_for_wrong_user() -> None:
    from app.services.home_card_service import HomeCardService

    session = AsyncMock()
    svc = HomeCardService(session, now=_NOW)
    svc._home_repo = AsyncMock()
    svc._home_repo.get_plant_for_user = AsyncMock(return_value=None)

    result = await svc.get_plant_card(_PLANT_ID, uuid.uuid4())
    assert result is None


# ---------------------------------------------------------------------------
# get_home: multi-plant list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_home_returns_card_per_plant() -> None:
    from app.services.home_card_service import HomeCardService

    session = AsyncMock()
    svc = HomeCardService(session, now=_NOW)

    p1, p2 = _make_plant(uuid.uuid4()), _make_plant(uuid.uuid4())
    svc._home_repo = AsyncMock()
    svc._home_repo.list_plants_by_user = AsyncMock(return_value=[p1, p2])
    svc._home_repo.get_species_profile = AsyncMock(return_value=None)
    svc._home_repo.get_latest_character = AsyncMock(return_value=None)
    svc._rule_repo = AsyncMock()
    svc._rule_repo.get_thresholds = AsyncMock(return_value=None)
    svc._rule_repo.get_recent_care_logs = AsyncMock(return_value=[])
    svc._rule_repo.get_latest_snapshot = AsyncMock(return_value=None)

    with patch("app.services.home_card_service._ENGINE") as mock_engine:
        mock_engine.evaluate.return_value = _make_rule_result()
        resp = await svc.get_home(_USER)

    assert resp.user_id == _USER
    assert len(resp.plants) == 2


@pytest.mark.asyncio
async def test_get_home_empty_when_no_plants() -> None:
    from app.services.home_card_service import HomeCardService

    session = AsyncMock()
    svc = HomeCardService(session, now=_NOW)
    svc._home_repo = AsyncMock()
    svc._home_repo.list_plants_by_user = AsyncMock(return_value=[])

    resp = await svc.get_home(_USER)

    assert resp.plants == []
