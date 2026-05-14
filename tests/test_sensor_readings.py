"""TICKET-054 — REST sensor readings endpoint transaction tests."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _make_req_body(**overrides) -> dict:
    base = {
        "reading_id": "r-rest-054-001",
        "device_id": "device-001",
        "plant_id": "plant-001",
        "measured_at": "2026-05-14T12:00:00+09:00",
        "temperature_c": 12.6,
        "humidity_pct": 44.8,
        "light_lux": 160.5,
        "soil_moisture_pct": 100.0,
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_rest_endpoint_commits_after_insert() -> None:
    from app.schemas.sensor_readings import SensorReadingResponse
    from app.services.sensor_ingest import SensorIngestService

    plant_id = uuid.uuid4()
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()

    from app.schemas.sensor_readings import SensorReadingRequest
    from app.api.sensor_readings import create_sensor_reading

    req = SensorReadingRequest.model_validate(_make_req_body())
    mock_response = SensorReadingResponse(status="inserted", ignored=False, reading_id="r-rest-054-001")

    with patch("app.api.sensor_readings.SensorIngestService") as mock_cls:
        mock_svc = AsyncMock()
        mock_svc.ingest.return_value = (mock_response, 201)
        mock_cls.return_value = mock_svc

        await create_sensor_reading(req, session=mock_session)

    mock_session.commit.assert_awaited_once()
    mock_session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_rest_endpoint_rolls_back_on_exception() -> None:
    from app.schemas.sensor_readings import SensorReadingRequest
    from app.api.sensor_readings import create_sensor_reading

    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()

    req = SensorReadingRequest.model_validate(_make_req_body())

    with patch("app.api.sensor_readings.SensorIngestService") as mock_cls:
        mock_svc = AsyncMock()
        mock_svc.ingest.side_effect = RuntimeError("DB error")
        mock_cls.return_value = mock_svc

        with pytest.raises(RuntimeError):
            await create_sensor_reading(req, session=mock_session)

    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_awaited()
