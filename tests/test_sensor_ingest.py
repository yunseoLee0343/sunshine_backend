"""TICKET-054 — SensorIngestService transaction tests."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _req(**overrides):
    from app.schemas.sensor_readings import SensorReadingRequest

    base = {
        "reading_id": "r-054-001",
        "device_id": "device-001",
        "plant_id": "plant-001",
        "measured_at": "2026-05-14T12:00:00+09:00",
        "temperature_c": 12.6,
        "humidity_pct": 44.8,
        "light_lux": 160.5,
        "soil_moisture_pct": 100.0,
    }
    base.update(overrides)
    return SensorReadingRequest.model_validate(base)


@pytest.mark.asyncio
async def test_ingest_does_not_commit() -> None:
    from app.services.sensor_ingest import SensorIngestService

    plant_id = uuid.uuid4()
    mock_plant = MagicMock()
    mock_plant.id = plant_id
    mock_plant.device_id = "device-001"

    mock_session = MagicMock()
    mock_session.commit = AsyncMock()

    svc = SensorIngestService(mock_session)

    with (
        patch.object(svc, "_resolve_plant", AsyncMock(return_value=mock_plant)),
        patch.object(svc.repo, "find_by_reading_id", AsyncMock(return_value=None)),
        patch.object(svc.repo, "insert", AsyncMock()),
    ):
        response, status_code = await svc.ingest(_req())

    assert status_code == 201
    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_ingest_sets_resolved_plant_id_after_insert() -> None:
    from app.services.sensor_ingest import SensorIngestService

    plant_id = uuid.uuid4()
    mock_plant = MagicMock()
    mock_plant.id = plant_id
    mock_plant.device_id = "device-001"

    mock_session = MagicMock()

    svc = SensorIngestService(mock_session)

    with (
        patch.object(svc, "_resolve_plant", AsyncMock(return_value=mock_plant)),
        patch.object(svc.repo, "find_by_reading_id", AsyncMock(return_value=None)),
        patch.object(svc.repo, "insert", AsyncMock()),
    ):
        await svc.ingest(_req())

    assert svc.resolved_plant_id == plant_id


@pytest.mark.asyncio
async def test_ingest_duplicate_does_not_commit() -> None:
    from app.services.sensor_ingest import SensorIngestService

    plant_id = uuid.uuid4()
    mock_plant = MagicMock()
    mock_plant.id = plant_id
    mock_plant.device_id = "device-001"
    existing = MagicMock()

    mock_session = MagicMock()
    mock_session.commit = AsyncMock()

    svc = SensorIngestService(mock_session)

    with (
        patch.object(svc, "_resolve_plant", AsyncMock(return_value=mock_plant)),
        patch.object(svc.repo, "find_by_reading_id", AsyncMock(return_value=existing)),
    ):
        response, status_code = await svc.ingest(_req())

    assert status_code == 200
    assert response.status == "duplicate_ignored"
    mock_session.commit.assert_not_awaited()
    assert svc.resolved_plant_id is None
