"""TICKET-053 — EnvironmentDetailService tests (snapshot + raw fallback)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_plant(plant_id: uuid.UUID) -> MagicMock:
    plant = MagicMock()
    plant.id = plant_id
    plant.nickname = "초록이"
    plant.room_name = "거실"
    return plant


def _make_snapshot(window: str, plant_id: uuid.UUID) -> MagicMock:
    snap = MagicMock()
    snap.window = window
    snap.window_start = datetime(2026, 5, 14, 3, 0, tzinfo=UTC)
    snap.window_end = datetime(2026, 5, 14, 12, 0, tzinfo=UTC)
    snap.temperature_avg_c = Decimal("24.0")
    snap.temperature_min_c = Decimal("23.0")
    snap.temperature_max_c = Decimal("25.0")
    snap.humidity_avg_pct = Decimal("51.0")
    snap.humidity_min_pct = Decimal("49.0")
    snap.humidity_max_pct = Decimal("53.0")
    snap.light_avg_lux = Decimal("830.0")
    snap.light_min_lux = Decimal("700.0")
    snap.light_max_lux = Decimal("950.0")
    snap.soil_moisture_avg_pct = Decimal("38.0")
    snap.soil_moisture_min_pct = Decimal("35.0")
    snap.soil_moisture_max_pct = Decimal("42.0")
    return snap


def _make_raw_reading(plant_id: uuid.UUID) -> MagicMock:
    reading = MagicMock()
    reading.measured_at = datetime(2026, 5, 14, 12, 0, tzinfo=UTC)
    reading.temperature_c = Decimal("24.2")
    reading.humidity_pct = Decimal("51.0")
    reading.light_lux = Decimal("830.0")
    reading.soil_moisture_pct = Decimal("38.0")
    return reading


@pytest.mark.asyncio
async def test_get_detail_returns_latest_from_snapshot() -> None:
    from app.services.environment_detail_service import EnvironmentDetailService

    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    plant = _make_plant(plant_id)
    latest_snap = _make_snapshot("latest", plant_id)

    mock_session = MagicMock()
    svc = EnvironmentDetailService(mock_session)

    def _snap_by_window(pid, w):
        return latest_snap if w == "latest" else None

    with (
        patch.object(svc._repo, "get_plant_for_user", AsyncMock(return_value=plant)),
        patch.object(svc._repo, "get_snapshot_by_window", AsyncMock(side_effect=_snap_by_window)),
        patch.object(svc._repo, "get_latest_character", AsyncMock(return_value=None)),
        patch.object(svc._repo, "get_latest_sensor_reading", AsyncMock(return_value=None)),
    ):
        result = await svc.get_detail(plant_id, user_id)

    assert result is not None
    assert result.latest is not None
    assert result.latest.window == "latest"
    assert result.latest.source == "snapshot"


@pytest.mark.asyncio
async def test_get_detail_falls_back_to_raw_reading_when_no_snapshot() -> None:
    from app.services.environment_detail_service import EnvironmentDetailService

    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    plant = _make_plant(plant_id)
    raw = _make_raw_reading(plant_id)

    mock_session = MagicMock()
    svc = EnvironmentDetailService(mock_session)

    with (
        patch.object(svc._repo, "get_plant_for_user", AsyncMock(return_value=plant)),
        patch.object(svc._repo, "get_snapshot_by_window", AsyncMock(return_value=None)),
        patch.object(svc._repo, "get_latest_character", AsyncMock(return_value=None)),
        patch.object(svc._repo, "get_latest_sensor_reading", AsyncMock(return_value=raw)),
    ):
        result = await svc.get_detail(plant_id, user_id)

    assert result is not None
    assert result.latest is not None
    assert result.latest.window == "latest"
    assert result.latest.source == "raw_sensor_reading_fallback"
    assert result.latest.sample_count == 1
    assert result.latest.temperature_c.avg == pytest.approx(24.2)


@pytest.mark.asyncio
async def test_get_detail_latest_is_none_when_no_snapshot_and_no_readings() -> None:
    from app.services.environment_detail_service import EnvironmentDetailService

    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    plant = _make_plant(plant_id)

    mock_session = MagicMock()
    svc = EnvironmentDetailService(mock_session)

    with (
        patch.object(svc._repo, "get_plant_for_user", AsyncMock(return_value=plant)),
        patch.object(svc._repo, "get_snapshot_by_window", AsyncMock(return_value=None)),
        patch.object(svc._repo, "get_latest_character", AsyncMock(return_value=None)),
        patch.object(svc._repo, "get_latest_sensor_reading", AsyncMock(return_value=None)),
    ):
        result = await svc.get_detail(plant_id, user_id)

    assert result is not None
    assert result.latest is None


@pytest.mark.asyncio
async def test_get_detail_returns_none_when_plant_not_found() -> None:
    from app.services.environment_detail_service import EnvironmentDetailService

    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    mock_session = MagicMock()
    svc = EnvironmentDetailService(mock_session)

    with patch.object(svc._repo, "get_plant_for_user", AsyncMock(return_value=None)):
        result = await svc.get_detail(plant_id, user_id)

    assert result is None
