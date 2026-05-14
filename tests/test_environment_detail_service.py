"""TICKET-053 / TICKET-054 — EnvironmentDetailService tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_plant(plant_id: uuid.UUID) -> MagicMock:
    plant = MagicMock()
    plant.id = plant_id
    plant.nickname = "초록이"
    plant.room_name = "거실"
    return plant


def _make_snapshot(window: str, window_end: datetime | None = None) -> MagicMock:
    snap = MagicMock()
    snap.window = window
    snap.window_start = datetime(2026, 5, 14, 3, 0, tzinfo=UTC)
    snap.window_end = window_end or datetime(2026, 5, 14, 12, 0, tzinfo=UTC)
    snap.temperature_avg_c = Decimal("22.0")
    snap.temperature_min_c = Decimal("21.0")
    snap.temperature_max_c = Decimal("23.0")
    snap.humidity_avg_pct = Decimal("58.0")
    snap.humidity_min_pct = Decimal("55.0")
    snap.humidity_max_pct = Decimal("61.0")
    snap.light_avg_lux = Decimal("1200.0")
    snap.light_min_lux = Decimal("800.0")
    snap.light_max_lux = Decimal("1600.0")
    snap.soil_moisture_avg_pct = Decimal("18.0")
    snap.soil_moisture_min_pct = Decimal("15.0")
    snap.soil_moisture_max_pct = Decimal("22.0")
    return snap


def _make_raw_reading(measured_at: datetime | None = None) -> MagicMock:
    reading = MagicMock()
    reading.measured_at = measured_at or datetime(2026, 5, 14, 12, 0, tzinfo=UTC)
    reading.temperature_c = Decimal("12.6")
    reading.humidity_pct = Decimal("44.8")
    reading.light_lux = Decimal("160.5")
    reading.soil_moisture_pct = Decimal("100.0")
    return reading


# ---------------------------------------------------------------------------
# Basic snapshot / fallback behaviour (TICKET-053)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_detail_returns_snapshot_when_no_newer_raw_reading() -> None:
    from app.services.environment_detail_service import EnvironmentDetailService

    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    plant = _make_plant(plant_id)
    snap_end = datetime(2026, 5, 14, 12, 0, tzinfo=UTC)
    latest_snap = _make_snapshot("latest", window_end=snap_end)
    # Raw reading is OLDER than snapshot → snapshot wins
    raw = _make_raw_reading(measured_at=snap_end - timedelta(hours=1))

    svc = EnvironmentDetailService(MagicMock())

    def _snap_by_window(pid, w):
        return latest_snap if w == "latest" else None

    with (
        patch.object(svc._repo, "get_plant_for_user", AsyncMock(return_value=plant)),
        patch.object(svc._repo, "get_snapshot_by_window", AsyncMock(side_effect=_snap_by_window)),
        patch.object(svc._repo, "get_latest_character", AsyncMock(return_value=None)),
        patch.object(svc._repo, "get_latest_sensor_reading", AsyncMock(return_value=raw)),
    ):
        result = await svc.get_detail(plant_id, user_id)

    assert result is not None
    assert result.latest is not None
    assert result.latest.source == "snapshot"
    assert result.latest.soil_moisture_pct.avg == pytest.approx(18.0)


@pytest.mark.asyncio
async def test_get_detail_returns_raw_when_newer_than_snapshot() -> None:
    """TICKET-054: stale snapshot detection — raw reading newer than snapshot."""
    from app.services.environment_detail_service import EnvironmentDetailService

    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    plant = _make_plant(plant_id)
    snap_end = datetime(2026, 5, 14, 12, 0, tzinfo=UTC)
    latest_snap = _make_snapshot("latest", window_end=snap_end)
    # Raw reading is NEWER than snapshot → raw wins
    raw = _make_raw_reading(measured_at=snap_end + timedelta(minutes=30))

    svc = EnvironmentDetailService(MagicMock())

    def _snap_by_window(pid, w):
        return latest_snap if w == "latest" else None

    with (
        patch.object(svc._repo, "get_plant_for_user", AsyncMock(return_value=plant)),
        patch.object(svc._repo, "get_snapshot_by_window", AsyncMock(side_effect=_snap_by_window)),
        patch.object(svc._repo, "get_latest_character", AsyncMock(return_value=None)),
        patch.object(svc._repo, "get_latest_sensor_reading", AsyncMock(return_value=raw)),
    ):
        result = await svc.get_detail(plant_id, user_id)

    assert result is not None
    assert result.latest is not None
    assert result.latest.source == "raw_sensor_reading_fallback"
    assert result.latest.soil_moisture_pct.avg == pytest.approx(100.0)
    assert result.latest.temperature_c.avg == pytest.approx(12.6)


@pytest.mark.asyncio
async def test_get_detail_falls_back_to_raw_when_no_snapshot() -> None:
    from app.services.environment_detail_service import EnvironmentDetailService

    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    plant = _make_plant(plant_id)
    raw = _make_raw_reading()

    svc = EnvironmentDetailService(MagicMock())

    with (
        patch.object(svc._repo, "get_plant_for_user", AsyncMock(return_value=plant)),
        patch.object(svc._repo, "get_snapshot_by_window", AsyncMock(return_value=None)),
        patch.object(svc._repo, "get_latest_character", AsyncMock(return_value=None)),
        patch.object(svc._repo, "get_latest_sensor_reading", AsyncMock(return_value=raw)),
    ):
        result = await svc.get_detail(plant_id, user_id)

    assert result is not None
    assert result.latest is not None
    assert result.latest.source == "raw_sensor_reading_fallback"
    assert result.latest.sample_count == 1
    assert result.latest.temperature_c.avg == pytest.approx(12.6)


@pytest.mark.asyncio
async def test_get_detail_latest_is_none_when_no_snapshot_and_no_readings() -> None:
    from app.services.environment_detail_service import EnvironmentDetailService

    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    plant = _make_plant(plant_id)

    svc = EnvironmentDetailService(MagicMock())

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

    svc = EnvironmentDetailService(MagicMock())

    with patch.object(svc._repo, "get_plant_for_user", AsyncMock(return_value=None)):
        result = await svc.get_detail(plant_id, user_id)

    assert result is None


@pytest.mark.asyncio
async def test_demo_seed_values_replaced_after_newer_mqtt_reading() -> None:
    """Regression: demo seed soil=18 is replaced when MQTT sends soil=100."""
    from app.services.environment_detail_service import EnvironmentDetailService

    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    plant = _make_plant(plant_id)

    # Demo seed snapshot window_end = 2024-01-15T12:00
    demo_snap_end = datetime(2024, 1, 15, 12, 0, tzinfo=UTC)
    demo_snap = _make_snapshot("latest", window_end=demo_snap_end)

    # MQTT reading comes in much later
    mqtt_ts = datetime(2026, 5, 14, 12, 27, tzinfo=UTC)
    raw = _make_raw_reading(measured_at=mqtt_ts)

    svc = EnvironmentDetailService(MagicMock())

    def _snap_by_window(pid, w):
        return demo_snap if w == "latest" else None

    with (
        patch.object(svc._repo, "get_plant_for_user", AsyncMock(return_value=plant)),
        patch.object(svc._repo, "get_snapshot_by_window", AsyncMock(side_effect=_snap_by_window)),
        patch.object(svc._repo, "get_latest_character", AsyncMock(return_value=None)),
        patch.object(svc._repo, "get_latest_sensor_reading", AsyncMock(return_value=raw)),
    ):
        result = await svc.get_detail(plant_id, user_id)

    assert result.latest is not None
    assert result.latest.source == "raw_sensor_reading_fallback"
    # Real MQTT value, not demo seed value
    assert result.latest.soil_moisture_pct.avg == pytest.approx(100.0)
    assert result.latest.temperature_c.avg == pytest.approx(12.6)
