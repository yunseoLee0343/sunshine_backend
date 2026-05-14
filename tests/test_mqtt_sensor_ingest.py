"""TICKET-053 / TICKET-054 — MqttSensorIngestService unit tests."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.mqtt.schemas import IngestOutcome


def _make_payload(**overrides) -> bytes:
    data = {
        "reading_id": "r-001",
        "device_id": "device-001",
        "plant_id": "plant-001",
        "measured_at": "2026-05-14T12:00:00+09:00",
        "temperature_c": 24.2,
        "humidity_pct": 51.0,
        "light_lux": 830.0,
        "soil_moisture_pct": 38.0,
    }
    data.update(overrides)
    return json.dumps(data).encode()


def _make_session() -> MagicMock:
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_invalid_topic_returns_invalid_topic_outcome() -> None:
    from app.services.mqtt_sensor_ingest import MqttSensorIngestService

    svc = MqttSensorIngestService(_make_session())
    result = await svc.process("bad/topic/extra/segment", _make_payload())
    assert result.outcome == IngestOutcome.invalid_topic
    assert result.snapshot_refreshed is False


@pytest.mark.asyncio
async def test_device_id_mismatch_returns_mismatch_outcome() -> None:
    from app.services.mqtt_sensor_ingest import MqttSensorIngestService

    svc = MqttSensorIngestService(_make_session())
    result = await svc.process(
        "sensor/readings/device-999",
        _make_payload(device_id="device-001"),
    )
    assert result.outcome == IngestOutcome.device_id_mismatch
    assert result.snapshot_refreshed is False


@pytest.mark.asyncio
async def test_inserted_outcome_commits_after_aggregate() -> None:
    from app.schemas.sensor_readings import SensorReadingResponse
    from app.services.mqtt_sensor_ingest import MqttSensorIngestService

    plant_id = uuid.uuid4()
    mock_session = _make_session()
    svc = MqttSensorIngestService(mock_session)

    mock_ingest_resp = SensorReadingResponse(status="inserted", ignored=False, reading_id="r-001")

    with (
        patch("app.services.mqtt_sensor_ingest.SensorIngestService") as mock_ingest_cls,
        patch("app.services.snapshot_service.SnapshotService") as mock_snap_cls,
    ):
        mock_ingest_instance = AsyncMock()
        mock_ingest_instance.ingest.return_value = (mock_ingest_resp, 201)
        mock_ingest_instance.resolved_plant_id = plant_id
        mock_ingest_cls.return_value = mock_ingest_instance

        mock_snap_instance = AsyncMock()
        mock_snap_cls.return_value = mock_snap_instance

        result = await svc.process("sensor/readings/device-001", _make_payload())

    assert result.outcome == IngestOutcome.inserted
    assert result.snapshot_refreshed is True
    assert result.plant_id == str(plant_id)
    mock_session.commit.assert_awaited_once()
    mock_snap_instance.aggregate.assert_awaited_once_with(plant_id)


@pytest.mark.asyncio
async def test_duplicate_reading_does_not_call_snapshot_aggregate() -> None:
    from app.schemas.sensor_readings import SensorReadingResponse
    from app.services.mqtt_sensor_ingest import MqttSensorIngestService

    mock_session = _make_session()
    svc = MqttSensorIngestService(mock_session)

    mock_dup_resp = SensorReadingResponse(status="duplicate_ignored", ignored=True, reading_id="r-001")

    with (
        patch("app.services.mqtt_sensor_ingest.SensorIngestService") as mock_ingest_cls,
        patch("app.services.snapshot_service.SnapshotService") as mock_snap_cls,
    ):
        mock_ingest_instance = AsyncMock()
        mock_ingest_instance.ingest.return_value = (mock_dup_resp, 200)
        mock_ingest_instance.resolved_plant_id = None
        mock_ingest_cls.return_value = mock_ingest_instance

        mock_snap_instance = AsyncMock()
        mock_snap_cls.return_value = mock_snap_instance

        result = await svc.process("sensor/readings/device-001", _make_payload())

    assert result.outcome == IngestOutcome.duplicate_ignored
    assert result.snapshot_refreshed is False
    mock_snap_instance.aggregate.assert_not_called()
    # Duplicate: no commit needed (nothing was written)
    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_snapshot_failure_rolls_back_and_returns_error() -> None:
    """TICKET-054: all-or-nothing — aggregate failure rolls back insert too."""
    from app.schemas.sensor_readings import SensorReadingResponse
    from app.services.mqtt_sensor_ingest import MqttSensorIngestService

    plant_id = uuid.uuid4()
    mock_session = _make_session()
    svc = MqttSensorIngestService(mock_session)

    mock_ingest_resp = SensorReadingResponse(status="inserted", ignored=False, reading_id="r-001")

    with (
        patch("app.services.mqtt_sensor_ingest.SensorIngestService") as mock_ingest_cls,
        patch("app.services.snapshot_service.SnapshotService") as mock_snap_cls,
    ):
        mock_ingest_instance = AsyncMock()
        mock_ingest_instance.ingest.return_value = (mock_ingest_resp, 201)
        mock_ingest_instance.resolved_plant_id = plant_id
        mock_ingest_cls.return_value = mock_ingest_instance

        mock_snap_instance = AsyncMock()
        mock_snap_instance.aggregate.side_effect = RuntimeError("DB down")
        mock_snap_cls.return_value = mock_snap_instance

        result = await svc.process("sensor/readings/device-001", _make_payload())

    assert result.outcome == IngestOutcome.error
    assert result.snapshot_refreshed is False
    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalid_payload_json_returns_invalid_payload() -> None:
    from app.services.mqtt_sensor_ingest import MqttSensorIngestService

    svc = MqttSensorIngestService(_make_session())
    result = await svc.process("sensor/readings/device-001", b"not json")
    assert result.outcome == IngestOutcome.invalid_payload
    assert result.snapshot_refreshed is False


@pytest.mark.asyncio
async def test_sunshine_topic_shape_accepted() -> None:
    from app.schemas.sensor_readings import SensorReadingResponse
    from app.services.mqtt_sensor_ingest import MqttSensorIngestService

    plant_id = uuid.uuid4()
    mock_session = _make_session()
    svc = MqttSensorIngestService(mock_session)

    mock_ingest_resp = SensorReadingResponse(status="inserted", ignored=False, reading_id="r-002")

    with (
        patch("app.services.mqtt_sensor_ingest.SensorIngestService") as mock_ingest_cls,
        patch("app.services.snapshot_service.SnapshotService") as mock_snap_cls,
    ):
        mock_ingest_instance = AsyncMock()
        mock_ingest_instance.ingest.return_value = (mock_ingest_resp, 201)
        mock_ingest_instance.resolved_plant_id = plant_id
        mock_ingest_cls.return_value = mock_ingest_instance

        mock_snap_instance = AsyncMock()
        mock_snap_cls.return_value = mock_snap_instance

        result = await svc.process(
            "sunshine/device-001/readings",
            _make_payload(reading_id="r-002"),
        )

    assert result.outcome == IngestOutcome.inserted
    assert result.snapshot_refreshed is True
