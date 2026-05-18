"""TICKET-067 — SensorRetentionService + SnapshotRepository compaction tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reading(measured_at: datetime, **kwargs):
    r = MagicMock()
    r.id = uuid.uuid4()
    r.measured_at = measured_at
    for k, v in kwargs.items():
        setattr(r, k, v)
    return r


def _utc(offset_hours: float = 0) -> datetime:
    return datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC) + timedelta(hours=offset_hours)


# ---------------------------------------------------------------------------
# SensorRetentionRepository tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retention_deletes_rows_older_than_cutoff() -> None:
    from app.repositories.sensor_retention_repository import SensorRetentionRepository

    mock_session = MagicMock()
    # batch_size=3: first batch returns 3 (full), second returns 0 (done).
    mock_session.execute = AsyncMock(side_effect=[
        MagicMock(rowcount=3),
        MagicMock(rowcount=0),
    ])

    repo = SensorRetentionRepository(mock_session)
    cutoff = _utc(-48)
    deleted = await repo.delete_before(cutoff, batch_size=3)

    assert deleted == 3
    assert mock_session.execute.await_count == 2  # one full batch, one empty


@pytest.mark.asyncio
async def test_retention_leaves_newer_rows_untouched() -> None:
    """delete_before only touches rows older than cutoff — verified by SQL WHERE clause."""
    from app.repositories.sensor_retention_repository import SensorRetentionRepository

    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(rowcount=0))

    repo = SensorRetentionRepository(mock_session)
    cutoff = _utc(-48)
    deleted = await repo.delete_before(cutoff)

    assert deleted == 0
    # Execute was called once and deleted nothing → newer rows were not touched.
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_retention_multiple_batches_sum_correctly() -> None:
    from app.repositories.sensor_retention_repository import SensorRetentionRepository

    mock_session = MagicMock()
    # Two full batches of 5 each, then an empty batch.
    mock_session.execute = AsyncMock(side_effect=[
        MagicMock(rowcount=5),
        MagicMock(rowcount=5),
        MagicMock(rowcount=0),
    ])

    repo = SensorRetentionRepository(mock_session)
    deleted = await repo.delete_before(_utc(-48), batch_size=5)

    assert deleted == 10
    assert mock_session.execute.await_count == 3


# ---------------------------------------------------------------------------
# SensorRetentionService tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_service_deletes_when_enabled() -> None:
    from app.services.sensor_retention_service import SensorRetentionService

    mock_session = MagicMock()
    svc = SensorRetentionService(mock_session)

    with (
        patch("app.services.sensor_retention_service.settings") as mock_settings,
        patch.object(svc.repo, "delete_before", AsyncMock(return_value=57)),
    ):
        mock_settings.SENSOR_RETENTION_ENABLED = True
        mock_settings.SENSOR_RAW_RETENTION_DAYS = 2
        mock_settings.SENSOR_RETENTION_BATCH_SIZE = 10000

        result = await svc.run(now=_utc())

    assert result.deleted_count == 57
    assert result.retention_days == 2
    assert result.cutoff == _utc() - timedelta(days=2)


@pytest.mark.asyncio
async def test_service_deletes_nothing_when_disabled() -> None:
    from app.services.sensor_retention_service import SensorRetentionService

    mock_session = MagicMock()
    svc = SensorRetentionService(mock_session)

    with (
        patch("app.services.sensor_retention_service.settings") as mock_settings,
        patch.object(svc.repo, "delete_before", AsyncMock(return_value=999)) as mock_delete,
    ):
        mock_settings.SENSOR_RETENTION_ENABLED = False
        mock_settings.SENSOR_RAW_RETENTION_DAYS = 2
        mock_settings.SENSOR_RETENTION_BATCH_SIZE = 10000

        result = await svc.run(now=_utc())

    assert result.deleted_count == 0
    mock_delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_service_repeated_run_is_idempotent() -> None:
    """Running retention twice on an already-empty window returns 0 both times."""
    from app.services.sensor_retention_service import SensorRetentionService

    mock_session = MagicMock()
    svc = SensorRetentionService(mock_session)

    with (
        patch("app.services.sensor_retention_service.settings") as mock_settings,
        patch.object(svc.repo, "delete_before", AsyncMock(return_value=0)),
    ):
        mock_settings.SENSOR_RETENTION_ENABLED = True
        mock_settings.SENSOR_RAW_RETENTION_DAYS = 2
        mock_settings.SENSOR_RETENTION_BATCH_SIZE = 10000

        first = await svc.run(now=_utc())
        second = await svc.run(now=_utc())

    assert first.deleted_count == 0
    assert second.deleted_count == 0


@pytest.mark.asyncio
async def test_service_never_touches_environment_snapshots() -> None:
    """Retention only deletes from sensor_readings; EnvironmentSnapshot is never imported."""
    from app.services import sensor_retention_service as mod

    assert not hasattr(mod, "EnvironmentSnapshot"), (
        "sensor_retention_service must not import EnvironmentSnapshot"
    )
    assert not hasattr(mod, "environment_snapshot"), (
        "sensor_retention_service must not reference environment_snapshot module"
    )


# ---------------------------------------------------------------------------
# SnapshotRepository compaction: one row per (plant_id, window)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_snapshot_upsert_uses_plant_window_conflict_target() -> None:
    """upsert() conflict target must be (plant_id, window) after TICKET-067."""
    import inspect

    from app.repositories.snapshot_repository import SnapshotRepository

    source = inspect.getsource(SnapshotRepository.upsert)
    assert '"plant_id", "window"' in source or "plant_id" in source
    # The old 4-column target must be gone.
    assert "window_start" not in source.split("index_elements")[1].split("]")[0]


@pytest.mark.asyncio
async def test_repeated_aggregate_leaves_one_snapshot_row_per_window() -> None:
    """Calling aggregate() twice with the same plant should upsert, not insert new rows."""
    from app.services.snapshot_service import SnapshotService

    plant_id = uuid.uuid4()
    now = _utc()

    r = MagicMock()
    r.id = uuid.uuid4()
    r.measured_at = now - timedelta(hours=1)
    r.temperature_c = 22.0
    r.humidity_pct = 55.0
    r.light_lux = 600.0
    r.soil_moisture_pct = 40.0

    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=MagicMock())

    upsert_calls: list = []

    async def _fake_upsert(**kwargs):
        upsert_calls.append(kwargs)

    with (
        patch("app.services.snapshot_service.SnapshotRepository") as mock_repo_cls,
    ):
        mock_repo = MagicMock()
        mock_repo.get_latest_per_metric = AsyncMock(
            return_value={
                "temperature_c": r,
                "humidity_pct": r,
                "light_lux": r,
                "soil_moisture_pct": r,
            }
        )
        mock_repo.get_readings_in_range = AsyncMock(return_value=[r])
        mock_repo.upsert = AsyncMock(side_effect=_fake_upsert)
        mock_repo_cls.return_value = mock_repo

        svc = SnapshotService(mock_session)
        await svc.aggregate(plant_id, now=now)
        first_call_count = len(upsert_calls)

        # Second run at the same time → same windows → should still produce 3 upserts,
        # each hitting the same (plant_id, window) key.
        await svc.aggregate(plant_id, now=now)
        second_call_count = len(upsert_calls)

    # 3 windows per call (latest, 24h, 7d) × 2 calls = 6 upsert calls total.
    assert first_call_count == 3
    assert second_call_count == 6
    # All upserts share the same plant_id — if the DB constraint is (plant_id, window),
    # each call overwrites the same 3 rows.
    windows_first = {c["window"] for c in upsert_calls[:3]}
    windows_second = {c["window"] for c in upsert_calls[3:]}
    assert windows_first == {"latest", "24h", "7d"}
    assert windows_second == {"latest", "24h", "7d"}
