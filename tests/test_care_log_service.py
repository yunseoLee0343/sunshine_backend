"""TICKET-011 — CareLogService unit tests (no DB)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.care_log import CareLog
from app.models.plant import Plant
from app.models.plant_character import PlantCharacter
from app.schemas.care_logs import CareLogRequest

_NOW = datetime(2026, 5, 10, 12, 0, 0, tzinfo=UTC)
_PLANT_ID = uuid.uuid4()
_USER_ID = uuid.uuid4()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_plant() -> Plant:
    p = MagicMock(spec=Plant)
    p.id = _PLANT_ID
    p.user_id = _USER_ID
    return p


def _req(action_type: str = "watering", note: str | None = None) -> CareLogRequest:
    return CareLogRequest(
        user_id=_USER_ID,
        action_type=action_type,  # type: ignore[arg-type]
        note=note,
        acted_at=_NOW,
    )


def _make_log(action_type: str = "watering") -> CareLog:
    log = MagicMock(spec=CareLog)
    log.id = uuid.uuid4()
    log.plant_id = _PLANT_ID
    log.action_type = action_type
    log.note = None
    log.acted_at = _NOW
    log.created_at = _NOW
    return log


async def _make_svc(plant: Plant | None = _make_plant()):
    from app.services.care_log_service import CareLogService

    session = AsyncMock()
    svc = CareLogService(session)
    svc._log_repo = AsyncMock()
    svc._log_repo.get_plant_for_user = AsyncMock(return_value=plant)
    svc._log_repo.create = AsyncMock(side_effect=lambda x: x)
    svc._log_repo.list_for_plant = AsyncMock(return_value=[])
    svc._char_repo = AsyncMock()
    svc._char_repo.create = AsyncMock(side_effect=lambda x: x)
    return svc, session


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


def test_request_rejects_unknown_action_type() -> None:
    with pytest.raises(Exception):
        CareLogRequest(user_id=_USER_ID, action_type="pruning", acted_at=_NOW)


def test_request_rejects_naive_acted_at() -> None:
    naive = datetime(2026, 5, 10, 12, 0, 0)
    with pytest.raises(Exception):
        CareLogRequest(user_id=_USER_ID, action_type="watering", acted_at=naive)


def test_request_rejects_extra_fields() -> None:
    with pytest.raises(Exception):
        CareLogRequest(
            user_id=_USER_ID, action_type="watering", acted_at=_NOW, bogus="x"
        )


# ---------------------------------------------------------------------------
# Ownership checks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_log_care_raises_when_plant_not_found() -> None:
    from app.services.care_log_service import PlantNotFoundError

    svc, _ = await _make_svc(plant=None)
    with pytest.raises(PlantNotFoundError):
        await svc.log_care(_PLANT_ID, _req())


@pytest.mark.asyncio
async def test_list_raises_when_plant_not_found() -> None:
    from app.services.care_log_service import PlantNotFoundError

    svc, _ = await _make_svc(plant=None)
    with pytest.raises(PlantNotFoundError):
        await svc.list_care_logs(_PLANT_ID, _USER_ID)


# ---------------------------------------------------------------------------
# Watering: care_log + character inserted atomically
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_watering_creates_care_log() -> None:
    svc, session = await _make_svc()
    result = await svc.log_care(_PLANT_ID, _req("watering"))
    svc._log_repo.create.assert_called_once()
    assert result.log.action_type == "watering"


@pytest.mark.asyncio
async def test_watering_creates_after_watering_character() -> None:
    svc, _ = await _make_svc()
    result = await svc.log_care(_PLANT_ID, _req("watering"))
    svc._char_repo.create.assert_called_once()
    assert result.character is not None
    assert result.character.reason_code == "after_watering"
    assert result.character.mood == "happy"


@pytest.mark.asyncio
async def test_watering_character_block_matches_engine_output() -> None:
    svc, _ = await _make_svc()
    result = await svc.log_care(_PLANT_ID, _req("watering"))
    c = result.character
    assert c.expression == "smile"
    assert c.status_message == "물을 마시고 기분이 좋아졌어요."
    assert c.primary_action == "none"


# ---------------------------------------------------------------------------
# Note: only care_log inserted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_note_creates_care_log() -> None:
    svc, _ = await _make_svc()
    result = await svc.log_care(_PLANT_ID, _req("note", note="물이 잘 흡수됐어요."))
    svc._log_repo.create.assert_called_once()
    assert result.log.action_type == "note"
    assert result.log.note == "물이 잘 흡수됐어요."


@pytest.mark.asyncio
async def test_note_does_not_touch_character() -> None:
    svc, _ = await _make_svc()
    result = await svc.log_care(_PLANT_ID, _req("note"))
    svc._char_repo.create.assert_not_called()
    assert result.character is None


# ---------------------------------------------------------------------------
# No rule engine or cascade
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_rule_engine_import_in_service() -> None:
    import app.services.care_log_service as mod

    src = open(mod.__file__, encoding="utf-8").read()
    for forbidden in ("rule_engine", "RuleEngine", "openai", "anthropic"):
        assert forbidden not in src, f"Forbidden: {forbidden!r} found in care_log_service"


# ---------------------------------------------------------------------------
# List care logs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_returns_newest_first_order() -> None:
    older = _make_log()
    older.acted_at = datetime(2026, 5, 1, tzinfo=UTC)
    newer = _make_log()
    newer.acted_at = datetime(2026, 5, 10, tzinfo=UTC)

    svc, _ = await _make_svc()
    svc._log_repo.list_for_plant = AsyncMock(return_value=[newer, older])
    result = await svc.list_care_logs(_PLANT_ID, _USER_ID)

    assert len(result.logs) == 2
    assert result.logs[0].acted_at >= result.logs[1].acted_at


@pytest.mark.asyncio
async def test_list_empty_when_no_logs() -> None:
    svc, _ = await _make_svc()
    result = await svc.list_care_logs(_PLANT_ID, _USER_ID)
    assert result.plant_id == _PLANT_ID
    assert result.logs == []
