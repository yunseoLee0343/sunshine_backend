"""TICKET-007 — SnapshotService unit tests (no live DB)."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.sensor_reading import SensorReading
from app.schemas.environment_snapshots import (
    AggregationSummary,
    EnvironmentSnapshotResult,
)
from app.services.snapshot_service import SnapshotService, _stats

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PLANT = uuid.uuid4()
_NOW = datetime(2026, 5, 10, 12, 0, 0, tzinfo=UTC)


def _reading(
    measured_at: datetime,
    temp: float = 22.0,
    humi: float = 55.0,
    light: float = 3000.0,
    soil: float = 40.0,
) -> SensorReading:
    r = MagicMock(spec=SensorReading)
    r.id = uuid.uuid4()
    r.reading_id = str(uuid.uuid4())
    r.device_id = "dev-test"
    r.plant_id = _PLANT
    r.measured_at = measured_at
    r.temperature_c = Decimal(str(temp))
    r.humidity_pct = Decimal(str(humi))
    r.light_lux = Decimal(str(light))
    r.soil_moisture_pct = Decimal(str(soil))
    r.created_at = datetime.now(UTC)
    return r


def _make_svc() -> tuple[SnapshotService, MagicMock]:
    session = MagicMock()
    svc = SnapshotService(session)
    return svc, session


# ---------------------------------------------------------------------------
# _stats helper
# ---------------------------------------------------------------------------


def test_stats_empty() -> None:
    s = _stats([], "temperature_c")
    assert s.avg is None and s.min is None and s.max is None


def test_stats_single() -> None:
    r = _reading(_NOW, temp=22.0)
    s = _stats([r], "temperature_c")
    assert s.avg == pytest.approx(22.0)
    assert s.min == pytest.approx(22.0)
    assert s.max == pytest.approx(22.0)


def test_stats_multiple() -> None:
    readings = [
        _reading(_NOW, temp=10.0),
        _reading(_NOW, temp=20.0),
        _reading(_NOW, temp=30.0),
    ]
    s = _stats(readings, "temperature_c")
    assert s.avg == pytest.approx(20.0)
    assert s.min == pytest.approx(10.0)
    assert s.max == pytest.approx(30.0)


# ---------------------------------------------------------------------------
# aggregate — all windows have data
# ---------------------------------------------------------------------------


def test_aggregate_all_windows_ok() -> None:
    svc, _ = _make_svc()
    r_latest = _reading(_NOW - timedelta(minutes=5), temp=21.0)
    r_24h = _reading(_NOW - timedelta(hours=12), temp=23.0)
    r_7d = _reading(_NOW - timedelta(days=3), temp=19.0)

    async def _go():
        with (
            patch.object(svc.repo, "get_latest_reading", new=AsyncMock(return_value=r_latest)),
            patch.object(
                svc.repo,
                "get_readings_in_range",
                new=AsyncMock(side_effect=[[r_24h], [r_7d]]),
            ),
            patch.object(svc.repo, "upsert", new=AsyncMock()),
        ):
            return await svc.aggregate(_PLANT, now=_NOW)

    summary = asyncio.run(_go())
    assert isinstance(summary, AggregationSummary)
    assert len(summary.snapshots) == 3
    windows = {s.window for s in summary.snapshots}
    assert windows == {"latest", "24h", "7d"}
    for snap in summary.snapshots:
        assert snap.status == "ok"
        assert snap.sample_count >= 1


# ---------------------------------------------------------------------------
# aggregate — missing_data when no readings
# ---------------------------------------------------------------------------


def test_aggregate_missing_data_latest() -> None:
    svc, _ = _make_svc()

    async def _go():
        with (
            patch.object(svc.repo, "get_latest_reading", new=AsyncMock(return_value=None)),
            patch.object(
                svc.repo, "get_readings_in_range", new=AsyncMock(return_value=[])
            ),
            patch.object(svc.repo, "upsert", new=AsyncMock()) as upsert_mock,
        ):
            summary = await svc.aggregate(_PLANT, now=_NOW)
            return summary, upsert_mock

    summary, upsert_mock = asyncio.run(_go())
    latest = next(s for s in summary.snapshots if s.window == "latest")
    assert latest.status == "missing_data"
    assert latest.sample_count == 0
    assert latest.temperature_c.avg is None
    # upsert must NOT be called when no data
    upsert_mock.assert_not_called()


def test_aggregate_missing_data_windows_not_persisted() -> None:
    svc, _ = _make_svc()

    async def _go():
        with (
            patch.object(svc.repo, "get_latest_reading", new=AsyncMock(return_value=None)),
            patch.object(
                svc.repo, "get_readings_in_range", new=AsyncMock(return_value=[])
            ),
            patch.object(svc.repo, "upsert", new=AsyncMock()) as mock_upsert,
        ):
            await svc.aggregate(_PLANT, now=_NOW)
            return mock_upsert

    mock_upsert = asyncio.run(_go())
    mock_upsert.assert_not_called()


# ---------------------------------------------------------------------------
# aggregate — upsert called for windows with data
# ---------------------------------------------------------------------------


def test_aggregate_upsert_called_for_data_windows() -> None:
    svc, _ = _make_svc()
    r = _reading(_NOW - timedelta(hours=1))

    async def _go():
        with (
            patch.object(svc.repo, "get_latest_reading", new=AsyncMock(return_value=r)),
            patch.object(
                svc.repo, "get_readings_in_range", new=AsyncMock(side_effect=[[r], [r]])
            ),
            patch.object(svc.repo, "upsert", new=AsyncMock()) as mock_upsert,
        ):
            await svc.aggregate(_PLANT, now=_NOW)
            return mock_upsert

    mock_upsert = asyncio.run(_go())
    # 3 windows all have data → 3 upserts
    assert mock_upsert.await_count == 3


# ---------------------------------------------------------------------------
# Window boundaries
# ---------------------------------------------------------------------------


def test_24h_window_boundaries() -> None:
    svc, _ = _make_svc()
    calls: list[tuple] = []

    async def _fake_range(plant_id, start, end):
        calls.append((start, end))
        return []

    async def _go():
        with (
            patch.object(svc.repo, "get_latest_reading", new=AsyncMock(return_value=None)),
            patch.object(svc.repo, "get_readings_in_range", new=AsyncMock(side_effect=_fake_range)),
            patch.object(svc.repo, "upsert", new=AsyncMock()),
        ):
            await svc.aggregate(_PLANT, now=_NOW)

    asyncio.run(_go())
    # First call is 24h, second is 7d
    start_24h, end_24h = calls[0]
    assert end_24h == _NOW
    assert (_NOW - start_24h) == timedelta(hours=24)


def test_7d_window_boundaries() -> None:
    svc, _ = _make_svc()
    calls: list[tuple] = []

    async def _fake_range(plant_id, start, end):
        calls.append((start, end))
        return []

    async def _go():
        with (
            patch.object(svc.repo, "get_latest_reading", new=AsyncMock(return_value=None)),
            patch.object(svc.repo, "get_readings_in_range", new=AsyncMock(side_effect=_fake_range)),
            patch.object(svc.repo, "upsert", new=AsyncMock()),
        ):
            await svc.aggregate(_PLANT, now=_NOW)

    asyncio.run(_go())
    start_7d, end_7d = calls[1]
    assert end_7d == _NOW
    assert (_NOW - start_7d) == timedelta(days=7)


# ---------------------------------------------------------------------------
# latest window uses reading's measured_at as window_start == window_end
# ---------------------------------------------------------------------------


def test_latest_window_timestamps_equal_reading_timestamp() -> None:
    svc, _ = _make_svc()
    ts = _NOW - timedelta(minutes=30)
    r = _reading(ts)

    async def _go():
        with (
            patch.object(svc.repo, "get_latest_reading", new=AsyncMock(return_value=r)),
            patch.object(
                svc.repo, "get_readings_in_range", new=AsyncMock(return_value=[])
            ),
            patch.object(svc.repo, "upsert", new=AsyncMock()),
        ):
            return await svc.aggregate(_PLANT, now=_NOW)

    summary = asyncio.run(_go())
    latest = next(s for s in summary.snapshots if s.window == "latest")
    assert latest.window_start == ts
    assert latest.window_end == ts


# ---------------------------------------------------------------------------
# Boundary — no Rule Engine, no character update
# ---------------------------------------------------------------------------


def test_no_character_engine_import() -> None:
    import app.services.snapshot_service as mod
    src = open(mod.__file__, encoding="utf-8").read()
    assert "character_state_engine" not in src
    assert "CharacterStateEngine" not in src
    assert "rule_engine" not in src.lower()


def test_returns_aggregation_summary_type() -> None:
    svc, _ = _make_svc()

    async def _go():
        with (
            patch.object(svc.repo, "get_latest_reading", new=AsyncMock(return_value=None)),
            patch.object(
                svc.repo, "get_readings_in_range", new=AsyncMock(return_value=[])
            ),
            patch.object(svc.repo, "upsert", new=AsyncMock()),
        ):
            return await svc.aggregate(_PLANT, now=_NOW)

    result = asyncio.run(_go())
    assert isinstance(result, AggregationSummary)
    assert result.plant_id == _PLANT
    assert len(result.snapshots) == 3
