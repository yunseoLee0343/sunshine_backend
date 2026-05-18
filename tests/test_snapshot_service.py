"""TICKET-007 / TICKET-066 / TICKET-068 — SnapshotService unit tests (no live DB)."""

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
)
from app.services.snapshot_service import (
    SnapshotService,
    _metric_stat,
    _rollup_stats,
    _stats,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PLANT = uuid.uuid4()
_NOW = datetime(2026, 5, 10, 12, 0, 0, tzinfo=UTC)


def _reading(
    measured_at: datetime,
    temp: float | None = 22.0,
    humi: float | None = 55.0,
    light: float | None = 3000.0,
    soil: float | None = 40.0,
) -> SensorReading:
    r = MagicMock(spec=SensorReading)
    r.id = uuid.uuid4()
    r.reading_id = str(uuid.uuid4())
    r.device_id = "dev-test"
    r.plant_id = _PLANT
    r.measured_at = measured_at
    r.temperature_c = Decimal(str(temp)) if temp is not None else None
    r.humidity_pct = Decimal(str(humi)) if humi is not None else None
    r.light_lux = Decimal(str(light)) if light is not None else None
    r.soil_moisture_pct = Decimal(str(soil)) if soil is not None else None
    r.created_at = datetime.now(UTC)
    return r


def _rollup(avg: float, min_: float, max_: float, count: int) -> MagicMock:
    r = MagicMock()
    r.avg_value = Decimal(str(avg))
    r.min_value = Decimal(str(min_))
    r.max_value = Decimal(str(max_))
    r.sample_count = count
    return r


def _all_same(r: SensorReading) -> dict:
    return {"temperature_c": r, "humidity_pct": r, "light_lux": r, "soil_moisture_pct": r}


def _all_none() -> dict:
    return {"temperature_c": None, "humidity_pct": None, "light_lux": None, "soil_moisture_pct": None}


def _make_svc() -> tuple[SnapshotService, MagicMock]:
    session = MagicMock()
    svc = SnapshotService(session)
    return svc, session


def _rollup_cls(per_metric: dict | None = None) -> MagicMock:
    """Return a mock SensorRollupRepository *class* whose instances return the given rollups."""
    per_metric = per_metric or {}

    async def _get_rollups(plant_id, metric_name, bucket, start, end):
        return per_metric.get(metric_name, [])

    mock_repo = MagicMock()
    mock_repo.get_rollups_in_range = _get_rollups
    return MagicMock(return_value=mock_repo)


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


def test_stats_null_values_skipped() -> None:
    """Readings with None for the metric are skipped (TICKET-066)."""
    r_with_temp = _reading(_NOW, temp=25.0, soil=None)
    r_no_temp = _reading(_NOW, temp=None, soil=30.0)
    s_temp = _stats([r_with_temp, r_no_temp], "temperature_c")
    assert s_temp.avg == pytest.approx(25.0)
    s_soil = _stats([r_with_temp, r_no_temp], "soil_moisture_pct")
    assert s_soil.avg == pytest.approx(30.0)


def test_stats_all_null_returns_none_stats() -> None:
    r = _reading(_NOW, temp=None)
    s = _stats([r], "temperature_c")
    assert s.avg is None and s.min is None and s.max is None


# ---------------------------------------------------------------------------
# _metric_stat helper
# ---------------------------------------------------------------------------


def test_metric_stat_none() -> None:
    s = _metric_stat(None)
    assert s.avg is None and s.min is None and s.max is None


def test_metric_stat_value() -> None:
    s = _metric_stat(42.0)
    assert s.avg == pytest.approx(42.0)
    assert s.min == pytest.approx(42.0)
    assert s.max == pytest.approx(42.0)


# ---------------------------------------------------------------------------
# _rollup_stats helper (TICKET-068)
# ---------------------------------------------------------------------------


def test_rollup_stats_empty() -> None:
    s = _rollup_stats([])
    assert s.avg is None and s.min is None and s.max is None


def test_rollup_stats_single() -> None:
    s = _rollup_stats([_rollup(22.0, 20.0, 24.0, 5)])
    assert s.avg == pytest.approx(22.0)
    assert s.min == pytest.approx(20.0)
    assert s.max == pytest.approx(24.0)


def test_rollup_stats_weighted_average() -> None:
    """Weighted average uses sample_count."""
    r1 = _rollup(10.0, 10.0, 10.0, 2)  # contributes 20
    r2 = _rollup(20.0, 20.0, 20.0, 8)  # contributes 160
    s = _rollup_stats([r1, r2])
    assert s.avg == pytest.approx(18.0)  # (20 + 160) / 10
    assert s.min == pytest.approx(10.0)
    assert s.max == pytest.approx(20.0)


def test_rollup_stats_null_avg_skipped() -> None:
    """Rollup rows with avg_value=None are excluded from computation."""
    null_row = MagicMock()
    null_row.avg_value = None
    null_row.sample_count = 5
    valid_row = _rollup(30.0, 30.0, 30.0, 3)
    s = _rollup_stats([null_row, valid_row])
    assert s.avg == pytest.approx(30.0)


# ---------------------------------------------------------------------------
# aggregate — all windows have data
# ---------------------------------------------------------------------------


def test_aggregate_all_windows_ok() -> None:
    svc, _ = _make_svc()
    r_latest = _reading(_NOW - timedelta(minutes=5), temp=21.0)
    r_24h = _reading(_NOW - timedelta(hours=12), temp=23.0)
    r7d = _rollup(19.0, 18.0, 20.0, 12)

    per_metric_7d = {
        "temperature_c": [r7d],
        "humidity_pct": [r7d],
        "light_lux": [r7d],
        "soil_moisture_pct": [r7d],
    }

    async def _go():
        with (
            patch.object(svc.repo, "get_latest_per_metric", new=AsyncMock(return_value=_all_same(r_latest))),
            patch.object(svc.repo, "get_readings_in_range", new=AsyncMock(return_value=[r_24h])),
            patch.object(svc.repo, "upsert", new=AsyncMock()),
            patch("app.services.snapshot_service.SensorRollupRepository", _rollup_cls(per_metric_7d)),
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
            patch.object(svc.repo, "get_latest_per_metric", new=AsyncMock(return_value=_all_none())),
            patch.object(svc.repo, "get_readings_in_range", new=AsyncMock(return_value=[])),
            patch.object(svc.repo, "upsert", new=AsyncMock()) as upsert_mock,
            patch("app.services.snapshot_service.SensorRollupRepository", _rollup_cls()),
        ):
            summary = await svc.aggregate(_PLANT, now=_NOW)
            return summary, upsert_mock

    summary, upsert_mock = asyncio.run(_go())
    latest = next(s for s in summary.snapshots if s.window == "latest")
    assert latest.status == "missing_data"
    assert latest.sample_count == 0
    assert latest.temperature_c.avg is None
    upsert_mock.assert_not_called()


def test_aggregate_missing_data_windows_not_persisted() -> None:
    svc, _ = _make_svc()

    async def _go():
        with (
            patch.object(svc.repo, "get_latest_per_metric", new=AsyncMock(return_value=_all_none())),
            patch.object(svc.repo, "get_readings_in_range", new=AsyncMock(return_value=[])),
            patch.object(svc.repo, "upsert", new=AsyncMock()) as mock_upsert,
            patch("app.services.snapshot_service.SensorRollupRepository", _rollup_cls()),
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
    r7d = _rollup(22.0, 20.0, 25.0, 5)
    per_metric_7d = {k: [r7d] for k in ("temperature_c", "humidity_pct", "light_lux", "soil_moisture_pct")}

    async def _go():
        with (
            patch.object(svc.repo, "get_latest_per_metric", new=AsyncMock(return_value=_all_same(r))),
            patch.object(svc.repo, "get_readings_in_range", new=AsyncMock(return_value=[r])),
            patch.object(svc.repo, "upsert", new=AsyncMock()) as mock_upsert,
            patch("app.services.snapshot_service.SensorRollupRepository", _rollup_cls(per_metric_7d)),
        ):
            await svc.aggregate(_PLANT, now=_NOW)
            return mock_upsert

    mock_upsert = asyncio.run(_go())
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
            patch.object(svc.repo, "get_latest_per_metric", new=AsyncMock(return_value=_all_none())),
            patch.object(svc.repo, "get_readings_in_range", new=AsyncMock(side_effect=_fake_range)),
            patch.object(svc.repo, "upsert", new=AsyncMock()),
            patch("app.services.snapshot_service.SensorRollupRepository", _rollup_cls()),
        ):
            await svc.aggregate(_PLANT, now=_NOW)

    asyncio.run(_go())
    start_24h, end_24h = calls[0]
    assert end_24h == _NOW
    assert (_NOW - start_24h) == timedelta(hours=24)


def test_7d_window_boundaries() -> None:
    """7d window: rollup repo is called with start=now-7d, end=now for each metric."""
    svc, _ = _make_svc()
    rollup_calls: list[tuple] = []

    async def _fake_get_rollups(plant_id, metric_name, bucket, start, end):
        rollup_calls.append((start, end))
        return []

    mock_repo = MagicMock()
    mock_repo.get_rollups_in_range = _fake_get_rollups
    mock_cls = MagicMock(return_value=mock_repo)

    async def _go():
        with (
            patch.object(svc.repo, "get_latest_per_metric", new=AsyncMock(return_value=_all_none())),
            patch.object(svc.repo, "get_readings_in_range", new=AsyncMock(return_value=[])),
            patch.object(svc.repo, "upsert", new=AsyncMock()),
            patch("app.services.snapshot_service.SensorRollupRepository", mock_cls),
        ):
            await svc.aggregate(_PLANT, now=_NOW)

    asyncio.run(_go())
    # 4 metrics × 1 call each
    assert len(rollup_calls) == 4
    start_7d, end_7d = rollup_calls[0]
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
            patch.object(svc.repo, "get_latest_per_metric", new=AsyncMock(return_value=_all_same(r))),
            patch.object(svc.repo, "get_readings_in_range", new=AsyncMock(return_value=[])),
            patch.object(svc.repo, "upsert", new=AsyncMock()),
            patch("app.services.snapshot_service.SensorRollupRepository", _rollup_cls()),
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
            patch.object(svc.repo, "get_latest_per_metric", new=AsyncMock(return_value=_all_none())),
            patch.object(svc.repo, "get_readings_in_range", new=AsyncMock(return_value=[])),
            patch.object(svc.repo, "upsert", new=AsyncMock()),
            patch("app.services.snapshot_service.SensorRollupRepository", _rollup_cls()),
        ):
            return await svc.aggregate(_PLANT, now=_NOW)

    result = asyncio.run(_go())
    assert isinstance(result, AggregationSummary)
    assert result.plant_id == _PLANT
    assert len(result.snapshots) == 3


# ---------------------------------------------------------------------------
# TICKET-066 — partial metrics: latest merges two devices
# ---------------------------------------------------------------------------


def test_latest_merges_two_partial_readings() -> None:
    """Two partial readings merge all four metrics in the latest snapshot."""
    svc, _ = _make_svc()
    ts_soil = _NOW - timedelta(minutes=2)
    ts_leaf = _NOW - timedelta(minutes=1)
    soil_reading = _reading(ts_soil, temp=None, humi=None, light=None, soil=42.0)
    leaf_reading = _reading(ts_leaf, temp=24.5, humi=55.2, light=850.0, soil=None)

    per_metric = {
        "temperature_c": leaf_reading,
        "humidity_pct": leaf_reading,
        "light_lux": leaf_reading,
        "soil_moisture_pct": soil_reading,
    }

    async def _go():
        with (
            patch.object(svc.repo, "get_latest_per_metric", new=AsyncMock(return_value=per_metric)),
            patch.object(svc.repo, "get_readings_in_range", new=AsyncMock(return_value=[])),
            patch.object(svc.repo, "upsert", new=AsyncMock()),
            patch("app.services.snapshot_service.SensorRollupRepository", _rollup_cls()),
        ):
            return await svc.aggregate(_PLANT, now=_NOW)

    summary = asyncio.run(_go())
    latest = next(s for s in summary.snapshots if s.window == "latest")
    assert latest.status == "ok"
    assert latest.temperature_c.avg == pytest.approx(24.5)
    assert latest.humidity_pct.avg == pytest.approx(55.2)
    assert latest.light_lux.avg == pytest.approx(850.0)
    assert latest.soil_moisture_pct.avg == pytest.approx(42.0)
    assert latest.window_start == ts_soil
    assert latest.window_end == ts_leaf


def test_latest_one_device_partial_nulls_no_crash() -> None:
    """Only soil sensor reported → temperature/humidity/light are None."""
    svc, _ = _make_svc()
    ts = _NOW - timedelta(minutes=5)
    soil_reading = _reading(ts, temp=None, humi=None, light=None, soil=38.0)

    per_metric = {
        "temperature_c": None,
        "humidity_pct": None,
        "light_lux": None,
        "soil_moisture_pct": soil_reading,
    }

    async def _go():
        with (
            patch.object(svc.repo, "get_latest_per_metric", new=AsyncMock(return_value=per_metric)),
            patch.object(svc.repo, "get_readings_in_range", new=AsyncMock(return_value=[])),
            patch.object(svc.repo, "upsert", new=AsyncMock()),
            patch("app.services.snapshot_service.SensorRollupRepository", _rollup_cls()),
        ):
            return await svc.aggregate(_PLANT, now=_NOW)

    summary = asyncio.run(_go())
    latest = next(s for s in summary.snapshots if s.window == "latest")
    assert latest.status == "ok"
    assert latest.temperature_c.avg is None
    assert latest.humidity_pct.avg is None
    assert latest.light_lux.avg is None
    assert latest.soil_moisture_pct.avg == pytest.approx(38.0)
    assert latest.window_start == ts
    assert latest.window_end == ts


def test_24h_aggregation_skips_null_per_metric() -> None:
    """24h window: readings with None temp are skipped for temperature stat."""
    svc, _ = _make_svc()
    r_soil_only = _reading(_NOW - timedelta(hours=1), temp=None, humi=None, light=None, soil=35.0)
    r_full = _reading(_NOW - timedelta(hours=2), temp=23.0, humi=60.0, light=1000.0, soil=40.0)

    async def _go():
        with (
            patch.object(svc.repo, "get_latest_per_metric", new=AsyncMock(return_value=_all_none())),
            patch.object(svc.repo, "get_readings_in_range", new=AsyncMock(return_value=[r_soil_only, r_full])),
            patch.object(svc.repo, "upsert", new=AsyncMock()),
            patch("app.services.snapshot_service.SensorRollupRepository", _rollup_cls()),
        ):
            return await svc.aggregate(_PLANT, now=_NOW)

    summary = asyncio.run(_go())
    snap_24h = next(s for s in summary.snapshots if s.window == "24h")
    assert snap_24h.status == "ok"
    # Only r_full has temperature_c → avg = 23.0
    assert snap_24h.temperature_c.avg == pytest.approx(23.0)
    # Both have soil_moisture_pct → avg = (35 + 40) / 2 = 37.5
    assert snap_24h.soil_moisture_pct.avg == pytest.approx(37.5)


def test_7d_aggregation_skips_null_per_metric() -> None:
    """7d window: rollup rows with None humidity are excluded from humidity stat."""
    svc, _ = _make_svc()

    # r_no_humi bucket: humidity=None, temp=20.0
    # r_full bucket:   humidity=58.0, temp=21.0
    # Humidity rollup: only one entry (from r_full) → avg=58.0
    # Temperature rollup: two entries (count=1 each) → weighted avg=20.5
    per_metric_7d = {
        "temperature_c": [_rollup(20.0, 20.0, 20.0, 1), _rollup(21.0, 21.0, 21.0, 1)],
        "humidity_pct": [_rollup(58.0, 58.0, 58.0, 1)],
        "light_lux": [_rollup(500.0, 500.0, 500.0, 1), _rollup(600.0, 600.0, 600.0, 1)],
        "soil_moisture_pct": [_rollup(30.0, 30.0, 30.0, 1), _rollup(32.0, 32.0, 32.0, 1)],
    }

    async def _go():
        with (
            patch.object(svc.repo, "get_latest_per_metric", new=AsyncMock(return_value=_all_none())),
            patch.object(svc.repo, "get_readings_in_range", new=AsyncMock(return_value=[])),
            patch.object(svc.repo, "upsert", new=AsyncMock()),
            patch("app.services.snapshot_service.SensorRollupRepository", _rollup_cls(per_metric_7d)),
        ):
            return await svc.aggregate(_PLANT, now=_NOW)

    summary = asyncio.run(_go())
    snap_7d = next(s for s in summary.snapshots if s.window == "7d")
    assert snap_7d.status == "ok"
    assert snap_7d.humidity_pct.avg == pytest.approx(58.0)
    assert snap_7d.temperature_c.avg == pytest.approx(20.5)  # (20*1 + 21*1) / 2


def test_7d_missing_rollups_returns_missing_data() -> None:
    """If no rollups exist for 7d, the window status is missing_data."""
    svc, _ = _make_svc()

    async def _go():
        with (
            patch.object(svc.repo, "get_latest_per_metric", new=AsyncMock(return_value=_all_none())),
            patch.object(svc.repo, "get_readings_in_range", new=AsyncMock(return_value=[])),
            patch.object(svc.repo, "upsert", new=AsyncMock()),
            patch("app.services.snapshot_service.SensorRollupRepository", _rollup_cls()),
        ):
            return await svc.aggregate(_PLANT, now=_NOW)

    summary = asyncio.run(_go())
    snap_7d = next(s for s in summary.snapshots if s.window == "7d")
    assert snap_7d.status == "missing_data"
    assert snap_7d.temperature_c.avg is None
