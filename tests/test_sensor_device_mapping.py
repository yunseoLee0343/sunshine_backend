"""S-001 — SensorIngestService device/plant ID mapping tests."""
import asyncio
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.sensor_readings import SensorReadingRequest
from app.services.sensor_ingest import SensorIngestService

_DEVICE_ID = "rpi-edge-node-01"
_EXTERNAL_ID = "plant-001"
_TS = "2026-05-07T15:30:00+09:00"


def _req(**overrides) -> SensorReadingRequest:
    base = {
        "reading_id": "r-map-001",
        "device_id": _DEVICE_ID,
        "plant_id": _EXTERNAL_ID,
        "measured_at": _TS,
        "temperature_c": 24.5,
        "humidity_pct": 55.2,
        "light_lux": 850.0,
        "soil_moisture_pct": 42.0,
    }
    base.update(overrides)
    return SensorReadingRequest.model_validate(base)


def _make_plant(*, plant_id: uuid.UUID | None = None, external_plant_id: str = _EXTERNAL_ID, device_id: str | None = _DEVICE_ID) -> MagicMock:
    p = MagicMock()
    p.id = plant_id or uuid.uuid4()
    p.external_plant_id = external_plant_id
    p.device_id = device_id
    return p


def _make_session(*, get_return=None) -> MagicMock:
    session = MagicMock()
    session.get = AsyncMock(return_value=get_return)
    session.commit = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# 4. plant_id UUID still works
# ---------------------------------------------------------------------------


def test_plant_id_uuid_resolves_directly() -> None:
    internal_id = uuid.uuid4()
    plant = _make_plant(plant_id=internal_id, external_plant_id=None, device_id=None)
    session = _make_session(get_return=plant)

    sensor_repo = MagicMock()
    sensor_repo.find_by_reading_id = AsyncMock(return_value=None)
    sensor_repo.insert = AsyncMock()

    async def _go():
        with patch("app.services.sensor_ingest.SensorRepository", return_value=sensor_repo):
            svc = SensorIngestService(session)
            req = _req(plant_id=str(internal_id), device_id="any-device")
            return await svc.ingest(req)

    response, code = asyncio.run(_go())
    assert response.status == "inserted"
    assert code == 201


# ---------------------------------------------------------------------------
# 5. External plant_id "plant-001" resolves to internal UUID
# ---------------------------------------------------------------------------


def test_external_plant_id_resolves_to_uuid() -> None:
    internal_id = uuid.uuid4()
    plant = _make_plant(plant_id=internal_id)

    session = _make_session()
    sensor_repo = MagicMock()
    sensor_repo.find_by_reading_id = AsyncMock(return_value=None)
    sensor_repo.insert = AsyncMock()

    plant_repo = MagicMock()
    plant_repo.find_by_external_plant_id = AsyncMock(return_value=plant)

    async def _go():
        with (
            patch("app.services.sensor_ingest.SensorRepository", return_value=sensor_repo),
            patch("app.services.sensor_ingest.PlantRepository", return_value=plant_repo),
        ):
            svc = SensorIngestService(session)
            return await svc.ingest(_req(plant_id=_EXTERNAL_ID))

    response, code = asyncio.run(_go())
    assert response.status == "inserted"
    assert code == 201
    # The internal UUID (not the string "plant-001") was passed to repo.insert
    _, kwargs = sensor_repo.insert.call_args
    assert kwargs["plant_id"] == internal_id


# ---------------------------------------------------------------------------
# 6. Unknown external plant_id returns plant_not_found
# ---------------------------------------------------------------------------


def test_unknown_external_plant_id_raises_404() -> None:
    from fastapi import HTTPException

    session = _make_session()
    plant_repo = MagicMock()
    plant_repo.find_by_external_plant_id = AsyncMock(return_value=None)
    sensor_repo = MagicMock()

    async def _go():
        with (
            patch("app.services.sensor_ingest.SensorRepository", return_value=sensor_repo),
            patch("app.services.sensor_ingest.PlantRepository", return_value=plant_repo),
        ):
            svc = SensorIngestService(session)
            return await svc.ingest(_req(plant_id="unknown-plant"))

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(_go())
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# 7. Duplicate reading_id returns duplicate_ignored
# ---------------------------------------------------------------------------


def test_duplicate_reading_id_returns_duplicate_ignored() -> None:
    internal_id = uuid.uuid4()
    plant = _make_plant(plant_id=internal_id)

    session = _make_session()
    sensor_repo = MagicMock()
    sensor_repo.find_by_reading_id = AsyncMock(return_value=MagicMock())  # already exists
    sensor_repo.insert = AsyncMock()

    plant_repo = MagicMock()
    plant_repo.find_by_external_plant_id = AsyncMock(return_value=plant)

    async def _go():
        with (
            patch("app.services.sensor_ingest.SensorRepository", return_value=sensor_repo),
            patch("app.services.sensor_ingest.PlantRepository", return_value=plant_repo),
        ):
            svc = SensorIngestService(session)
            return await svc.ingest(_req())

    response, code = asyncio.run(_go())
    assert response.status == "duplicate_ignored"
    assert response.ignored is True
    assert code == 200
    sensor_repo.insert.assert_not_awaited()


# ---------------------------------------------------------------------------
# device_id verification — plant.device_id set but mismatched → not found
# ---------------------------------------------------------------------------


def test_device_id_mismatch_on_plant_returns_not_found() -> None:
    from fastapi import HTTPException

    plant = _make_plant(device_id="other-device")
    session = _make_session()
    plant_repo = MagicMock()
    plant_repo.find_by_external_plant_id = AsyncMock(return_value=plant)
    sensor_repo = MagicMock()

    async def _go():
        with (
            patch("app.services.sensor_ingest.SensorRepository", return_value=sensor_repo),
            patch("app.services.sensor_ingest.PlantRepository", return_value=plant_repo),
        ):
            svc = SensorIngestService(session)
            # payload device_id = _DEVICE_ID, plant.device_id = "other-device"
            return await svc.ingest(_req(plant_id=_EXTERNAL_ID, device_id=_DEVICE_ID))

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(_go())
    assert exc_info.value.status_code == 404


def test_device_id_none_on_plant_skips_check() -> None:
    """If plant.device_id is None, any device_id payload is accepted."""
    internal_id = uuid.uuid4()
    plant = _make_plant(plant_id=internal_id, device_id=None)

    session = _make_session()
    sensor_repo = MagicMock()
    sensor_repo.find_by_reading_id = AsyncMock(return_value=None)
    sensor_repo.insert = AsyncMock()

    plant_repo = MagicMock()
    plant_repo.find_by_external_plant_id = AsyncMock(return_value=plant)

    async def _go():
        with (
            patch("app.services.sensor_ingest.SensorRepository", return_value=sensor_repo),
            patch("app.services.sensor_ingest.PlantRepository", return_value=plant_repo),
        ):
            svc = SensorIngestService(session)
            return await svc.ingest(_req(plant_id=_EXTERNAL_ID, device_id="any-device"))

    response, code = asyncio.run(_go())
    assert response.status == "inserted"
    assert code == 201
