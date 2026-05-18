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


# ---- TICKET-066: partial payload schema validation ----


def test_soil_only_payload_validates() -> None:
    from app.schemas.sensor_readings import SensorReadingRequest

    req = SensorReadingRequest.model_validate({
        "reading_id": "r-soil-01",
        "device_id": "esp32-soil-01",
        "plant_id": "plant-001",
        "measured_at": "2026-05-14T12:00:00+09:00",
        "soil_moisture_pct": 45.0,
    })
    assert req.soil_moisture_pct == 45.0
    assert req.temperature_c is None
    assert req.humidity_pct is None
    assert req.light_lux is None


def test_leaf_env_only_payload_validates() -> None:
    from app.schemas.sensor_readings import SensorReadingRequest

    req = SensorReadingRequest.model_validate({
        "reading_id": "r-leaf-01",
        "device_id": "esp32-leaf-01",
        "plant_id": "plant-001",
        "measured_at": "2026-05-14T12:00:00+09:00",
        "temperature_c": 22.5,
        "humidity_pct": 60.0,
        "light_lux": 500.0,
    })
    assert req.soil_moisture_pct is None
    assert req.light_lux == 500.0


def test_no_metrics_fails_validation() -> None:
    from pydantic import ValidationError

    from app.schemas.sensor_readings import SensorReadingRequest

    with pytest.raises(ValidationError, match="at least one metric"):
        SensorReadingRequest.model_validate({
            "reading_id": "r-no-metrics",
            "device_id": "esp32-soil-01",
            "plant_id": "plant-001",
            "measured_at": "2026-05-14T12:00:00+09:00",
        })


# ---- TICKET-066: multi-device _resolve_plant ----


@pytest.mark.asyncio
async def test_resolve_plant_accepts_esp32_soil_via_device_table() -> None:
    from unittest.mock import patch

    from app.services.sensor_ingest import SensorIngestService

    plant_id = uuid.uuid4()
    mock_plant = MagicMock()
    mock_plant.id = plant_id

    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_plant)

    svc = SensorIngestService(mock_session)

    with patch("app.services.sensor_ingest.PlantSensorDeviceRepository") as mock_repo_cls:
        mock_repo = MagicMock()
        mock_repo.find_active = AsyncMock(return_value=MagicMock())
        mock_repo_cls.return_value = mock_repo

        result = await svc._resolve_plant(str(plant_id), "esp32-soil-01")

    assert result is mock_plant
    mock_repo.find_active.assert_awaited_once_with(plant_id, "esp32-soil-01")


@pytest.mark.asyncio
async def test_resolve_plant_accepts_esp32_leaf_via_device_table() -> None:
    from unittest.mock import patch

    from app.services.sensor_ingest import SensorIngestService

    plant_id = uuid.uuid4()
    mock_plant = MagicMock()
    mock_plant.id = plant_id

    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_plant)

    svc = SensorIngestService(mock_session)

    with patch("app.services.sensor_ingest.PlantSensorDeviceRepository") as mock_repo_cls:
        mock_repo = MagicMock()
        mock_repo.find_active = AsyncMock(return_value=MagicMock())
        mock_repo_cls.return_value = mock_repo

        result = await svc._resolve_plant(str(plant_id), "esp32-leaf-01")

    assert result is mock_plant
    mock_repo.find_active.assert_awaited_once_with(plant_id, "esp32-leaf-01")


@pytest.mark.asyncio
async def test_resolve_plant_rejects_unknown_device() -> None:
    from unittest.mock import patch

    from app.services.sensor_ingest import SensorIngestService

    plant_id = uuid.uuid4()
    mock_plant = MagicMock()
    mock_plant.id = plant_id
    mock_plant.device_id = "esp32-soil-01"  # legacy field set — different from request

    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_plant)

    svc = SensorIngestService(mock_session)

    with patch("app.services.sensor_ingest.PlantSensorDeviceRepository") as mock_repo_cls:
        mock_repo = MagicMock()
        mock_repo.find_active = AsyncMock(return_value=None)
        mock_repo_cls.return_value = mock_repo

        result = await svc._resolve_plant(str(plant_id), "esp32-unknown-99")

    assert result is None


@pytest.mark.asyncio
async def test_resolve_plant_legacy_device_id_fallback() -> None:
    """No device-table row — legacy plant.device_id match still succeeds."""
    from unittest.mock import patch

    from app.services.sensor_ingest import SensorIngestService

    plant_id = uuid.uuid4()
    mock_plant = MagicMock()
    mock_plant.id = plant_id
    mock_plant.device_id = "device-legacy"

    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_plant)

    svc = SensorIngestService(mock_session)

    with patch("app.services.sensor_ingest.PlantSensorDeviceRepository") as mock_repo_cls:
        mock_repo = MagicMock()
        mock_repo.find_active = AsyncMock(return_value=None)
        mock_repo_cls.return_value = mock_repo

        result = await svc._resolve_plant(str(plant_id), "device-legacy")

    assert result is mock_plant


@pytest.mark.asyncio
async def test_resolve_plant_external_id_resolves_to_uuid() -> None:
    from unittest.mock import patch

    from app.services.sensor_ingest import SensorIngestService

    plant_id = uuid.uuid4()
    mock_plant = MagicMock()
    mock_plant.id = plant_id
    mock_plant.device_id = None

    mock_session = MagicMock()

    svc = SensorIngestService(mock_session)

    with (
        patch("app.services.sensor_ingest.PlantRepository") as mock_plant_repo_cls,
        patch("app.services.sensor_ingest.PlantSensorDeviceRepository") as mock_device_repo_cls,
    ):
        mock_plant_repo = MagicMock()
        mock_plant_repo.find_by_external_plant_id = AsyncMock(return_value=mock_plant)
        mock_plant_repo_cls.return_value = mock_plant_repo

        mock_device_repo = MagicMock()
        mock_device_repo.find_active = AsyncMock(return_value=None)
        mock_device_repo_cls.return_value = mock_device_repo

        result = await svc._resolve_plant("plant-001", "device-001")

    assert result is mock_plant
    mock_plant_repo.find_by_external_plant_id.assert_awaited_once_with("plant-001")
