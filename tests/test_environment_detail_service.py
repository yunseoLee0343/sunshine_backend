"""TICKET-010 — EnvironmentDetailService unit tests (no DB)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.environment_snapshot import EnvironmentSnapshot
from app.models.plant import Plant
from app.models.plant_character import PlantCharacter

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
    p.nickname = "몬스테라"
    p.room_name = "거실"
    return p


def _make_snapshot(window: str = "latest") -> EnvironmentSnapshot:
    s = MagicMock(spec=EnvironmentSnapshot)
    s.window = window
    s.window_start = _NOW
    s.window_end = _NOW
    s.temperature_avg_c = Decimal("22.5")
    s.temperature_min_c = Decimal("20.0")
    s.temperature_max_c = Decimal("25.0")
    s.humidity_avg_pct = Decimal("60.0")
    s.humidity_min_pct = Decimal("55.0")
    s.humidity_max_pct = Decimal("65.0")
    s.light_avg_lux = Decimal("3000.0")
    s.light_min_lux = Decimal("1000.0")
    s.light_max_lux = Decimal("5000.0")
    s.soil_moisture_avg_pct = Decimal("45.0")
    s.soil_moisture_min_pct = Decimal("40.0")
    s.soil_moisture_max_pct = Decimal("50.0")
    return s


def _make_char(reason_code: str = "good") -> PlantCharacter:
    c = MagicMock(spec=PlantCharacter)
    c.reason_code = reason_code
    return c


async def _make_svc(
    *,
    plant: Plant | None = None,
    latest: EnvironmentSnapshot | None = None,
    snap_24h: EnvironmentSnapshot | None = None,
    snap_7d: EnvironmentSnapshot | None = None,
    char: PlantCharacter | None = None,
):
    from app.services.environment_detail_service import EnvironmentDetailService

    session = AsyncMock()
    svc = EnvironmentDetailService(session)
    svc._repo = AsyncMock()
    svc._repo.get_plant_for_user = AsyncMock(return_value=plant)

    async def _get_snapshot(pid, window):
        return {"latest": latest, "24h": snap_24h, "7d": snap_7d}.get(window)

    svc._repo.get_snapshot_by_window = AsyncMock(side_effect=_get_snapshot)
    svc._repo.get_latest_character = AsyncMock(return_value=char)
    return svc


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_returns_none_for_unknown_plant() -> None:
    svc = await _make_svc(plant=None)
    result = await svc.get_detail(_PLANT_ID, _USER_ID)
    assert result is None


@pytest.mark.asyncio
async def test_returns_none_for_wrong_user() -> None:
    svc = await _make_svc(plant=None)  # repo returns None for wrong user
    result = await svc.get_detail(_PLANT_ID, uuid.uuid4())
    assert result is None


# ---------------------------------------------------------------------------
# Snapshot mapping
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_snapshots_null_when_no_data() -> None:
    svc = await _make_svc(plant=_make_plant())
    result = await svc.get_detail(_PLANT_ID, _USER_ID)
    assert result is not None
    assert result.latest is None
    assert result.summary_24h is None
    assert result.summary_7d is None


@pytest.mark.asyncio
async def test_latest_snapshot_mapped_correctly() -> None:
    snap = _make_snapshot("latest")
    svc = await _make_svc(plant=_make_plant(), latest=snap)
    result = await svc.get_detail(_PLANT_ID, _USER_ID)
    assert result.latest is not None
    assert result.latest.window == "latest"
    assert result.latest.temperature_c.avg == 22.5
    assert result.latest.humidity_pct.min == 55.0
    assert result.latest.soil_moisture_pct.avg == 45.0


@pytest.mark.asyncio
async def test_24h_and_7d_snapshots_mapped() -> None:
    svc = await _make_svc(
        plant=_make_plant(),
        snap_24h=_make_snapshot("24h"),
        snap_7d=_make_snapshot("7d"),
    )
    result = await svc.get_detail(_PLANT_ID, _USER_ID)
    assert result.summary_24h is not None
    assert result.summary_24h.window == "24h"
    assert result.summary_7d is not None
    assert result.summary_7d.window == "7d"


@pytest.mark.asyncio
async def test_partial_snapshots_null_when_missing() -> None:
    svc = await _make_svc(
        plant=_make_plant(),
        latest=_make_snapshot("latest"),
        # 24h and 7d absent
    )
    result = await svc.get_detail(_PLANT_ID, _USER_ID)
    assert result.latest is not None
    assert result.summary_24h is None
    assert result.summary_7d is None


@pytest.mark.asyncio
async def test_none_metric_values_preserved() -> None:
    snap = _make_snapshot("latest")
    snap.temperature_avg_c = None
    snap.temperature_min_c = None
    snap.temperature_max_c = None
    svc = await _make_svc(plant=_make_plant(), latest=snap)
    result = await svc.get_detail(_PLANT_ID, _USER_ID)
    assert result.latest.temperature_c.avg is None
    assert result.latest.temperature_c.min is None


# ---------------------------------------------------------------------------
# Character explanation templates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_character_gives_null_explanation() -> None:
    svc = await _make_svc(plant=_make_plant(), char=None)
    result = await svc.get_detail(_PLANT_ID, _USER_ID)
    assert result.character_explanation is None


@pytest.mark.asyncio
@pytest.mark.parametrize("reason_code,expected_fragment", [
    ("good", "건강한"),
    ("low_soil_moisture", "토양 수분 부족"),
    ("low_light", "빛 부족"),
    ("unstable_humidity", "습도 또는 온도 불안정"),
    ("after_watering", "물 주기"),
    ("onboarding_created", "새로 등록"),
])
async def test_explanation_template_mapped(reason_code: str, expected_fragment: str) -> None:
    svc = await _make_svc(plant=_make_plant(), char=_make_char(reason_code))
    result = await svc.get_detail(_PLANT_ID, _USER_ID)
    assert result.character_explanation is not None
    assert result.character_explanation.reason_code == reason_code
    assert expected_fragment in result.character_explanation.explanation


@pytest.mark.asyncio
async def test_unknown_reason_code_gets_fallback() -> None:
    svc = await _make_svc(plant=_make_plant(), char=_make_char("future_unknown_code"))
    result = await svc.get_detail(_PLANT_ID, _USER_ID)
    assert result.character_explanation is not None
    assert result.character_explanation.explanation  # non-empty fallback


# ---------------------------------------------------------------------------
# Plant metadata
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_plant_metadata_in_response() -> None:
    svc = await _make_svc(plant=_make_plant())
    result = await svc.get_detail(_PLANT_ID, _USER_ID)
    assert result.plant_id == _PLANT_ID
    assert result.nickname == "몬스테라"
    assert result.room_name == "거실"


# ---------------------------------------------------------------------------
# No DB mutations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_writes_during_get_detail() -> None:
    session = AsyncMock()
    from app.services.environment_detail_service import EnvironmentDetailService

    svc = EnvironmentDetailService(session)
    svc._repo = AsyncMock()
    svc._repo.get_plant_for_user = AsyncMock(return_value=_make_plant())
    svc._repo.get_snapshot_by_window = AsyncMock(return_value=None)
    svc._repo.get_latest_character = AsyncMock(return_value=None)

    await svc.get_detail(_PLANT_ID, _USER_ID)

    session.add.assert_not_called()
    session.flush.assert_not_called()
    session.commit.assert_not_called()
