"""TICKET-053 — SensorIngestService exposes plant_id for snapshot refresh."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_ingest_sets_resolved_plant_id_on_insert() -> None:
    from app.schemas.sensor_readings import SensorReadingRequest
    from app.services.sensor_ingest import SensorIngestService

    plant_id = uuid.uuid4()
    mock_plant = MagicMock()
    mock_plant.id = plant_id
    mock_plant.device_id = "device-001"

    mock_session = MagicMock()
    svc = SensorIngestService(mock_session)

    req = SensorReadingRequest(
        reading_id="r-snap-001",
        device_id="device-001",
        plant_id=str(plant_id),
        measured_at="2026-05-14T12:00:00+00:00",
        temperature_c=24.2,
        humidity_pct=51.0,
        light_lux=830.0,
        soil_moisture_pct=38.0,
    )

    mock_session.flush = AsyncMock()

    with (
        patch.object(svc, "_resolve_plant", AsyncMock(return_value=mock_plant)),
        patch.object(svc.repo, "find_by_reading_id", AsyncMock(return_value=None)),
        patch.object(svc.repo, "insert", AsyncMock()),
    ):
        response, status_code = await svc.ingest(req)

    assert status_code == 201
    assert svc.resolved_plant_id == plant_id


@pytest.mark.asyncio
async def test_ingest_resolved_plant_id_is_none_on_duplicate() -> None:
    from app.models.sensor_reading import SensorReading
    from app.schemas.sensor_readings import SensorReadingRequest
    from app.services.sensor_ingest import SensorIngestService

    plant_id = uuid.uuid4()
    mock_plant = MagicMock()
    mock_plant.id = plant_id
    mock_plant.device_id = "device-001"
    existing_row = MagicMock(spec=SensorReading)

    mock_session = MagicMock()
    svc = SensorIngestService(mock_session)

    req = SensorReadingRequest(
        reading_id="r-dup-001",
        device_id="device-001",
        plant_id=str(plant_id),
        measured_at="2026-05-14T12:00:00+00:00",
        temperature_c=24.2,
        humidity_pct=51.0,
        light_lux=830.0,
        soil_moisture_pct=38.0,
    )

    with (
        patch.object(svc, "_resolve_plant", AsyncMock(return_value=mock_plant)),
        patch.object(svc.repo, "find_by_reading_id", AsyncMock(return_value=existing_row)),
    ):
        response, status_code = await svc.ingest(req)

    assert status_code == 200
    assert response.status == "duplicate_ignored"
    assert svc.resolved_plant_id is None
