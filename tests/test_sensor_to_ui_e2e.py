"""TICKET-053 — end-to-end sensor-to-UI flow (pure unit, no DB)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_mqtt_insert_then_detail_returns_latest() -> None:
    """After an MQTT insert+snapshot-refresh, EnvironmentDetailService should
    return a non-null `latest` WindowSnapshot."""
    import json

    from app.mqtt.schemas import IngestOutcome
    from app.schemas.sensor_readings import SensorReadingResponse
    from app.services.environment_detail_service import EnvironmentDetailService
    from app.services.mqtt_sensor_ingest import MqttSensorIngestService

    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # ---- MQTT ingest ----
    mock_session = MagicMock()
    ingest_svc = MqttSensorIngestService(mock_session)

    mock_ingest_resp = SensorReadingResponse(status="inserted", ignored=False, reading_id="r-e2e-001")

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

        payload = json.dumps({
            "reading_id": "r-e2e-001",
            "device_id": "dev-001",
            "plant_id": str(plant_id),
            "measured_at": "2026-05-14T12:00:00+09:00",
            "temperature_c": 24.2,
            "humidity_pct": 51.0,
            "light_lux": 830.0,
            "soil_moisture_pct": 38.0,
        }).encode()

        result = await ingest_svc.process("sensor/readings/dev-001", payload)

    assert result.outcome == IngestOutcome.inserted
    assert result.snapshot_refreshed is True
    mock_snap_instance.aggregate.assert_called_once_with(plant_id)

    # ---- Environment detail ----
    plant = MagicMock()
    plant.id = plant_id
    plant.nickname = "초록이"
    plant.room_name = "거실"

    snap = MagicMock()
    snap.window = "latest"
    snap.window_start = datetime(2026, 5, 14, 12, 0, tzinfo=UTC)
    snap.window_end = datetime(2026, 5, 14, 12, 0, tzinfo=UTC)
    snap.temperature_avg_c = Decimal("24.2")
    snap.temperature_min_c = Decimal("24.2")
    snap.temperature_max_c = Decimal("24.2")
    snap.humidity_avg_pct = Decimal("51.0")
    snap.humidity_min_pct = Decimal("51.0")
    snap.humidity_max_pct = Decimal("51.0")
    snap.light_avg_lux = Decimal("830.0")
    snap.light_min_lux = Decimal("830.0")
    snap.light_max_lux = Decimal("830.0")
    snap.soil_moisture_avg_pct = Decimal("38.0")
    snap.soil_moisture_min_pct = Decimal("38.0")
    snap.soil_moisture_max_pct = Decimal("38.0")

    detail_svc = EnvironmentDetailService(MagicMock())

    with (
        patch.object(detail_svc._repo, "get_plant_for_user", AsyncMock(return_value=plant)),
        patch.object(
            detail_svc._repo,
            "get_snapshot_by_window",
            AsyncMock(side_effect=lambda pid, w: snap if w == "latest" else None),
        ),
        patch.object(detail_svc._repo, "get_latest_character", AsyncMock(return_value=None)),
        patch.object(detail_svc._repo, "get_latest_sensor_reading", AsyncMock(return_value=None)),
    ):
        detail = await detail_svc.get_detail(plant_id, user_id)

    assert detail is not None
    assert detail.latest is not None
    assert detail.latest.window == "latest"
    assert detail.latest.soil_moisture_pct.avg == pytest.approx(38.0)
