"""TICKET-006 — MqttSensorIngestService unit tests (no live broker/DB)."""

import asyncio
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.mqtt.schemas import IngestOutcome
from app.services.mqtt_sensor_ingest import MqttSensorIngestService

_PLANT_ID = str(uuid.uuid4())
_DEVICE_ID = "dev-001"
_TOPIC = f"sensor/readings/{_DEVICE_ID}"


def _valid_payload(**overrides) -> bytes:
    base = {
        "reading_id": "r-mqtt-001",
        "device_id": _DEVICE_ID,
        "plant_id": _PLANT_ID,
        "measured_at": "2026-05-10T10:00:00+00:00",
        "temperature_c": 22.0,
        "humidity_pct": 55.0,
        "light_lux": 3000.0,
        "soil_moisture_pct": 40.0,
    }
    base.update(overrides)
    return json.dumps(base).encode()


def _make_svc() -> tuple[MqttSensorIngestService, MagicMock]:
    session = MagicMock()
    session.commit = AsyncMock()
    svc = MqttSensorIngestService(session)
    return svc, session


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


def test_inserted_outcome() -> None:
    svc, _ = _make_svc()
    from app.schemas.sensor_readings import SensorReadingResponse

    async def _go():
        with patch(
            "app.services.mqtt_sensor_ingest.SensorIngestService.ingest",
            new=AsyncMock(
                return_value=(
                    SensorReadingResponse(status="inserted", ignored=False, reading_id="r-mqtt-001"),
                    201,
                )
            ),
        ):
            return await svc.process(_TOPIC, _valid_payload())

    result = asyncio.run(_go())
    assert result.outcome == IngestOutcome.inserted
    assert result.reading_id == "r-mqtt-001"


def test_duplicate_ignored_outcome() -> None:
    svc, _ = _make_svc()
    from app.schemas.sensor_readings import SensorReadingResponse

    async def _go():
        with patch(
            "app.services.mqtt_sensor_ingest.SensorIngestService.ingest",
            new=AsyncMock(
                return_value=(
                    SensorReadingResponse(
                        status="duplicate_ignored",
                        ignored=True,
                        reading_id="r-mqtt-001",
                    ),
                    200,
                )
            ),
        ):
            return await svc.process(_TOPIC, _valid_payload())

    result = asyncio.run(_go())
    assert result.outcome == IngestOutcome.duplicate_ignored


# ---------------------------------------------------------------------------
# Rejection paths
# ---------------------------------------------------------------------------


def test_invalid_topic_rejected() -> None:
    svc, _ = _make_svc()
    result = asyncio.run(svc.process("sensor/readings/", _valid_payload()))
    assert result.outcome == IngestOutcome.invalid_topic


def test_invalid_json_rejected() -> None:
    svc, _ = _make_svc()
    result = asyncio.run(svc.process(_TOPIC, b"not-json"))
    assert result.outcome == IngestOutcome.invalid_payload


def test_invalid_schema_rejected() -> None:
    svc, _ = _make_svc()
    # temperature out of range
    result = asyncio.run(svc.process(_TOPIC, _valid_payload(temperature_c=999.0)))
    assert result.outcome == IngestOutcome.invalid_payload


def test_device_id_mismatch_rejected() -> None:
    svc, _ = _make_svc()
    # topic says dev-001, payload says different-device
    result = asyncio.run(svc.process(_TOPIC, _valid_payload(device_id="different-device")))
    assert result.outcome == IngestOutcome.device_id_mismatch


def test_plant_not_found() -> None:
    from fastapi import HTTPException

    svc, _ = _make_svc()

    async def _go():
        with patch(
            "app.services.mqtt_sensor_ingest.SensorIngestService.ingest",
            new=AsyncMock(side_effect=HTTPException(status_code=404, detail="plant not found")),
        ):
            return await svc.process(_TOPIC, _valid_payload())

    result = asyncio.run(_go())
    assert result.outcome == IngestOutcome.plant_not_found


def test_naive_timestamp_rejected() -> None:
    svc, _ = _make_svc()
    result = asyncio.run(svc.process(_TOPIC, _valid_payload(measured_at="2026-05-10T10:00:00")))
    assert result.outcome == IngestOutcome.invalid_payload


# ---------------------------------------------------------------------------
# Boundary — no new DB logic, delegates to SensorIngestService
# ---------------------------------------------------------------------------


def test_delegates_to_sensor_ingest_service() -> None:
    """MqttSensorIngestService must call SensorIngestService.ingest, not its own DB code."""
    from app.schemas.sensor_readings import SensorReadingResponse

    svc, _ = _make_svc()
    ingest_mock = AsyncMock(
        return_value=(
            SensorReadingResponse(status="inserted", ignored=False, reading_id="r-mqtt-001"),
            201,
        )
    )

    async def _go():
        with patch(
            "app.services.mqtt_sensor_ingest.SensorIngestService.ingest",
            new=ingest_mock,
        ):
            return await svc.process(_TOPIC, _valid_payload())

    asyncio.run(_go())
    ingest_mock.assert_awaited_once()
