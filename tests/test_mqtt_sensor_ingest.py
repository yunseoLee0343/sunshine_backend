"""TICKET-053 — MqttSensorIngestService unit tests."""

from __future__ import annotations

import json
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


@pytest.mark.asyncio
async def test_invalid_topic_returns_invalid_topic_outcome() -> None:
    from app.services.mqtt_sensor_ingest import MqttSensorIngestService

    svc = MqttSensorIngestService(MagicMock())
    result = await svc.process("bad/topic/extra/segment", _make_payload())
    assert result.outcome == IngestOutcome.invalid_topic
    assert result.snapshot_refreshed is False


@pytest.mark.asyncio
async def test_device_id_mismatch_returns_mismatch_outcome() -> None:
    from app.services.mqtt_sensor_ingest import MqttSensorIngestService

    svc = MqttSensorIngestService(MagicMock())
    result = await svc.process(
        "sensor/readings/device-999",
        _make_payload(device_id="device-001"),
    )
    assert result.outcome == IngestOutcome.device_id_mismatch
    assert result.snapshot_refreshed is False


@pytest.mark.asyncio
async def test_inserted_outcome_calls_snapshot_aggregate() -> None:
    import uuid

    from app.schemas.sensor_readings import SensorReadingResponse
    from app.services.mqtt_sensor_ingest import MqttSensorIngestService

    plant_id = uuid.uuid4()
    mock_session = MagicMock()
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


@pytest.mark.asyncio
async def test_duplicate_reading_does_not_call_snapshot_aggregate() -> None:
    from app.schemas.sensor_readings import SensorReadingResponse
    from app.services.mqtt_sensor_ingest import MqttSensorIngestService

    mock_session = MagicMock()
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


@pytest.mark.asyncio
async def test_snapshot_failure_does_not_lose_inserted_reading() -> None:
    import uuid

    from app.schemas.sensor_readings import SensorReadingResponse
    from app.services.mqtt_sensor_ingest import MqttSensorIngestService

    plant_id = uuid.uuid4()
    mock_session = MagicMock()
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

    # Reading was inserted; snapshot failed but outcome is still inserted
    assert result.outcome == IngestOutcome.inserted
    assert result.snapshot_refreshed is False


@pytest.mark.asyncio
async def test_invalid_payload_json_returns_invalid_payload() -> None:
    from app.services.mqtt_sensor_ingest import MqttSensorIngestService

    svc = MqttSensorIngestService(MagicMock())
    result = await svc.process("sensor/readings/device-001", b"not json")
    assert result.outcome == IngestOutcome.invalid_payload
    assert result.snapshot_refreshed is False


@pytest.mark.asyncio
async def test_sunshine_topic_shape_accepted() -> None:
    import uuid

    from app.schemas.sensor_readings import SensorReadingResponse
    from app.services.mqtt_sensor_ingest import MqttSensorIngestService

    plant_id = uuid.uuid4()
    mock_session = MagicMock()
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
