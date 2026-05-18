"""TICKET-068 — SensorRollupService + SensorRollupRepository unit tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PLANT = uuid.uuid4()
_METRICS = ("temperature_c", "humidity_pct", "light_lux", "soil_moisture_pct")


def _utc(hours_offset: float = 0) -> datetime:
    return datetime(2026, 5, 10, 12, 0, 0, tzinfo=UTC) + timedelta(hours=hours_offset)


def _reading(measured_at: datetime, **metrics) -> MagicMock:
    r = MagicMock()
    r.id = uuid.uuid4()
    r.plant_id = _PLANT
    r.measured_at = measured_at
    for m in _METRICS:
        setattr(r, m, metrics.get(m))
    return r


def _rollup_row(metric_name: str, avg: float, min_: float, max_: float, count: int) -> MagicMock:
    r = MagicMock()
    r.avg_value = Decimal(str(avg))
    r.min_value = Decimal(str(min_))
    r.max_value = Decimal(str(max_))
    r.sample_count = count
    r.metric_name = metric_name
    return r


# ---------------------------------------------------------------------------
# SensorRollupRepository.rollup_raw_readings
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rollup_creates_hourly_buckets_from_raw_readings() -> None:
    """12 readings in one hour → one bucket per metric."""
    from app.repositories.sensor_rollup_repository import SensorRollupRepository

    readings = [
        _reading(
            _utc() + timedelta(minutes=i * 5),
            temperature_c=20.0 + i * 0.1,
            humidity_pct=50.0,
            light_lux=None,
            soil_moisture_pct=None,
        )
        for i in range(12)
    ]

    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = readings
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = SensorRollupRepository(mock_session)
    buckets = await repo.rollup_raw_readings(_PLANT, _utc(), _utc(1))

    # Two metrics with data: temperature_c and humidity_pct
    assert len(buckets) == 2
    temp_bucket = next(b for b in buckets if b.metric_name == "temperature_c")
    humi_bucket = next(b for b in buckets if b.metric_name == "humidity_pct")

    assert temp_bucket.sample_count == 12
    assert temp_bucket.avg_value == pytest.approx(sum(20.0 + i * 0.1 for i in range(12)) / 12)
    assert humi_bucket.sample_count == 12
    assert humi_bucket.avg_value == pytest.approx(50.0)


@pytest.mark.asyncio
async def test_rollup_skips_null_metric_values() -> None:
    """Null metric values in raw readings are excluded from rollup buckets."""
    from app.repositories.sensor_rollup_repository import SensorRollupRepository

    readings = [
        _reading(_utc(), temperature_c=22.0, humidity_pct=None, light_lux=None, soil_moisture_pct=None),
        _reading(_utc(timedelta(minutes=5).total_seconds() / 3600), temperature_c=None, humidity_pct=55.0, light_lux=None, soil_moisture_pct=None),
    ]

    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = readings
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = SensorRollupRepository(mock_session)
    buckets = await repo.rollup_raw_readings(_PLANT, _utc(-1), _utc(1))

    metric_names = {b.metric_name for b in buckets}
    # light_lux and soil_moisture_pct are all null → no buckets
    assert "light_lux" not in metric_names
    assert "soil_moisture_pct" not in metric_names
    # temperature_c: only reading[0] has it
    temp = next(b for b in buckets if b.metric_name == "temperature_c")
    assert temp.sample_count == 1
    assert temp.avg_value == pytest.approx(22.0)


@pytest.mark.asyncio
async def test_rollup_two_devices_partial_metrics_separate_buckets() -> None:
    """Two devices in the same hour: each contributes to different metrics."""
    from app.repositories.sensor_rollup_repository import SensorRollupRepository

    # Device A: soil only
    r_soil = _reading(_utc(), temperature_c=None, humidity_pct=None, light_lux=None, soil_moisture_pct=45.0)
    # Device B: temp+humi+light
    r_leaf = _reading(_utc(timedelta(minutes=1).total_seconds() / 3600), temperature_c=22.0, humidity_pct=58.0, light_lux=700.0, soil_moisture_pct=None)

    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [r_soil, r_leaf]
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = SensorRollupRepository(mock_session)
    buckets = await repo.rollup_raw_readings(_PLANT, _utc(-1), _utc(1))

    by_metric = {b.metric_name: b for b in buckets}
    assert "soil_moisture_pct" in by_metric
    assert "temperature_c" in by_metric
    assert by_metric["soil_moisture_pct"].sample_count == 1
    assert by_metric["soil_moisture_pct"].avg_value == pytest.approx(45.0)
    assert by_metric["temperature_c"].avg_value == pytest.approx(22.0)


@pytest.mark.asyncio
async def test_rollup_no_readings_returns_empty() -> None:
    from app.repositories.sensor_rollup_repository import SensorRollupRepository

    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = SensorRollupRepository(mock_session)
    buckets = await repo.rollup_raw_readings(_PLANT, _utc(-24), _utc())

    assert buckets == []


# ---------------------------------------------------------------------------
# SensorRollupService.rollup — idempotency and summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rollup_service_returns_correct_summary() -> None:
    from app.services.sensor_rollup_service import SensorRollupService

    mock_session = MagicMock()
    svc = SensorRollupService(mock_session)

    from app.repositories.sensor_rollup_repository import RollupBucket

    fake_buckets = [
        RollupBucket(
            plant_id=_PLANT, metric_name="temperature_c", bucket="hourly",
            bucket_start=_utc(-2), bucket_end=_utc(-1),
            avg_value=21.0, min_value=20.0, max_value=22.0, sample_count=12,
        ),
        RollupBucket(
            plant_id=_PLANT, metric_name="humidity_pct", bucket="hourly",
            bucket_start=_utc(-2), bucket_end=_utc(-1),
            avg_value=55.0, min_value=50.0, max_value=60.0, sample_count=12,
        ),
    ]

    with (
        patch.object(svc.repo, "rollup_raw_readings", AsyncMock(return_value=fake_buckets)),
        patch.object(svc.repo, "upsert_rollup", AsyncMock()) as mock_upsert,
    ):
        summary = await svc.rollup(_PLANT, start=_utc(-7 * 24), end=_utc())

    assert summary.bucket == "hourly"
    assert summary.created_or_updated == 2
    assert mock_upsert.await_count == 2


@pytest.mark.asyncio
async def test_rollup_service_idempotent_on_empty_readings() -> None:
    """Running rollup twice on empty raw data returns 0 both times."""
    from app.services.sensor_rollup_service import SensorRollupService

    mock_session = MagicMock()
    svc = SensorRollupService(mock_session)

    with (
        patch.object(svc.repo, "rollup_raw_readings", AsyncMock(return_value=[])),
        patch.object(svc.repo, "upsert_rollup", AsyncMock()),
    ):
        first = await svc.rollup(_PLANT, start=_utc(-168), end=_utc())
        second = await svc.rollup(_PLANT, start=_utc(-168), end=_utc())

    assert first.created_or_updated == 0
    assert second.created_or_updated == 0


# ---------------------------------------------------------------------------
# 7d snapshot uses rollups — after raw rows older than 2 days are deleted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_7d_snapshot_from_rollups_survives_raw_deletion() -> None:
    """SnapshotService can compute a 7d window from rollups when raw rows are gone."""
    from app.services.snapshot_service import SnapshotService

    mock_session = MagicMock()
    svc = SnapshotService(mock_session)

    # Simulate: raw readings older than 2 days deleted → 24h has data, 7d uses rollups
    r_24h = MagicMock()
    r_24h.id = uuid.uuid4()
    r_24h.measured_at = _utc(-12)
    for m in _METRICS:
        setattr(r_24h, m, Decimal("22.0"))

    rollup_per_metric = {
        "temperature_c": [_rollup_row("temperature_c", 20.5, 18.0, 23.0, 144)],
        "humidity_pct": [_rollup_row("humidity_pct", 55.0, 48.0, 62.0, 144)],
        "light_lux": [_rollup_row("light_lux", 600.0, 100.0, 1200.0, 144)],
        "soil_moisture_pct": [_rollup_row("soil_moisture_pct", 38.0, 30.0, 45.0, 144)],
    }

    async def _get_rollups(plant_id, metric_name, bucket, start, end):
        return rollup_per_metric.get(metric_name, [])

    mock_rollup_repo = MagicMock()
    mock_rollup_repo.get_rollups_in_range = _get_rollups
    mock_rollup_cls = MagicMock(return_value=mock_rollup_repo)

    with (
        patch.object(svc.repo, "get_latest_per_metric", AsyncMock(
            return_value={m: r_24h for m in _METRICS}
        )),
        patch.object(svc.repo, "get_readings_in_range", AsyncMock(return_value=[r_24h])),
        patch.object(svc.repo, "upsert", AsyncMock()),
        patch("app.services.snapshot_service.SensorRollupRepository", mock_rollup_cls),
    ):
        summary = await svc.aggregate(_PLANT, now=_utc())

    snap_7d = next(s for s in summary.snapshots if s.window == "7d")
    assert snap_7d.status == "ok"
    assert snap_7d.temperature_c.avg == pytest.approx(20.5)
    assert snap_7d.humidity_pct.avg == pytest.approx(55.0)
    assert snap_7d.sample_count == 144 * 4  # total across all 4 metrics


# ---------------------------------------------------------------------------
# Weighted average uses sample_count
# ---------------------------------------------------------------------------


def test_weighted_average_uses_sample_count() -> None:
    """A rollup with more samples contributes proportionally more to the average."""
    from app.services.snapshot_service import _rollup_stats

    r1 = _rollup_row("temperature_c", 10.0, 10.0, 10.0, 1)
    r2 = _rollup_row("temperature_c", 20.0, 20.0, 20.0, 9)
    s = _rollup_stats([r1, r2])
    # (10*1 + 20*9) / 10 = 190/10 = 19.0
    assert s.avg == pytest.approx(19.0)
    assert s.min == pytest.approx(10.0)
    assert s.max == pytest.approx(20.0)


# ---------------------------------------------------------------------------
# Missing rollups produce safe missing_data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_rollups_produce_missing_data_status() -> None:
    """When no rollups exist, the 7d window returns missing_data without crashing."""
    from app.services.snapshot_service import SnapshotService

    mock_session = MagicMock()
    svc = SnapshotService(mock_session)

    async def _no_rollups(plant_id, metric_name, bucket, start, end):
        return []

    mock_rollup_repo = MagicMock()
    mock_rollup_repo.get_rollups_in_range = _no_rollups
    mock_rollup_cls = MagicMock(return_value=mock_rollup_repo)

    with (
        patch.object(svc.repo, "get_latest_per_metric", AsyncMock(
            return_value={m: None for m in _METRICS}
        )),
        patch.object(svc.repo, "get_readings_in_range", AsyncMock(return_value=[])),
        patch.object(svc.repo, "upsert", AsyncMock()),
        patch("app.services.snapshot_service.SensorRollupRepository", mock_rollup_cls),
    ):
        summary = await svc.aggregate(_PLANT, now=_utc())

    snap_7d = next(s for s in summary.snapshots if s.window == "7d")
    assert snap_7d.status == "missing_data"
    assert snap_7d.temperature_c.avg is None
    assert snap_7d.sample_count == 0
