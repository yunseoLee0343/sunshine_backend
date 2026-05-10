"""TICKET-005 — Sensor Reading Ingestion tests (no live DB)."""

import asyncio
import uuid
from datetime import UTC, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.sensor_readings import get_session
from app.main import app
from app.schemas.sensor_readings import SensorReadingRequest, SensorReadingResponse

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TZ = timezone.utc
_PLANT_ID = uuid.uuid4()
_DEVICE_ID = "dev-001"


def _valid_payload(**overrides) -> dict:
    base = {
        "reading_id": "r-001",
        "device_id": _DEVICE_ID,
        "plant_id": str(_PLANT_ID),
        "measured_at": "2026-05-10T10:00:00+00:00",
        "temperature_c": 22.5,
        "humidity_pct": 55.0,
        "light_lux": 3000.0,
        "soil_moisture_pct": 40.0,
    }
    base.update(overrides)
    return base


async def _post(body: dict) -> tuple[int, dict]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/sensor-readings", json=body)
    return r.status_code, r.json()


def _make_plant():
    from app.models.plant import Plant
    now = datetime.now(UTC)
    return Plant(
        id=_PLANT_ID,
        user_id=uuid.uuid4(),
        species_profile_id=None,
        nickname="테스트",
        room_name=None,
        created_at=now,
        updated_at=now,
    )


def _fake_session_factory(plant=None, existing_reading=None):
    sess = MagicMock()
    sess.get = AsyncMock(return_value=plant)
    sess.add = MagicMock()
    sess.flush = AsyncMock()
    sess.commit = AsyncMock()
    return sess


# ---------------------------------------------------------------------------
# Schema validation — reading_id charset
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rid", [
    "abc123",
    "r-001",
    "sensor_01",
    "device:01.read",
])
def test_valid_reading_id_charset(rid: str) -> None:
    SensorReadingRequest(**{**_valid_payload(), "reading_id": rid})


@pytest.mark.parametrize("rid", [
    "has space",
    "bang!",
    "slash/",
    "hash#tag",
    "",
])
def test_invalid_reading_id_charset(rid: str) -> None:
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        SensorReadingRequest(**{**_valid_payload(), "reading_id": rid})


# ---------------------------------------------------------------------------
# Schema validation — measured_at timezone-awareness
# ---------------------------------------------------------------------------


def test_measured_at_naive_rejected() -> None:
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        SensorReadingRequest(**{**_valid_payload(), "measured_at": "2026-05-10T10:00:00"})


def test_measured_at_aware_accepted() -> None:
    req = SensorReadingRequest(**_valid_payload())
    assert req.measured_at.tzinfo is not None


# ---------------------------------------------------------------------------
# Schema validation — numeric ranges
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field,bad_val", [
    ("temperature_c", -41.0),
    ("temperature_c", 81.0),
    ("humidity_pct", -0.1),
    ("humidity_pct", 100.1),
    ("light_lux", -1.0),
    ("light_lux", 200_001.0),
    ("soil_moisture_pct", -0.1),
    ("soil_moisture_pct", 100.1),
])
def test_out_of_range_values_rejected(field: str, bad_val: float) -> None:
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        SensorReadingRequest(**{**_valid_payload(), field: bad_val})


@pytest.mark.parametrize("field", [
    "temperature_c", "humidity_pct", "light_lux", "soil_moisture_pct",
])
def test_nan_rejected(field: str) -> None:
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        SensorReadingRequest(**{**_valid_payload(), field: float("nan")})


@pytest.mark.parametrize("field", [
    "temperature_c", "humidity_pct", "light_lux", "soil_moisture_pct",
])
def test_infinity_rejected(field: str) -> None:
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        SensorReadingRequest(**{**_valid_payload(), field: float("inf")})


# ---------------------------------------------------------------------------
# API — happy path: new reading returns 201
# ---------------------------------------------------------------------------


def test_new_reading_returns_201() -> None:
    plant = _make_plant()

    async def _dep():
        sess = _fake_session_factory(plant=plant)
        with (
            patch(
                "app.services.sensor_ingest.SensorRepository.find_by_reading_id",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.services.sensor_ingest.SensorRepository.insert",
                new=AsyncMock(),
            ),
        ):
            yield sess

    app.dependency_overrides[get_session] = _dep
    try:
        status, body = asyncio.run(_post(_valid_payload()))
    finally:
        app.dependency_overrides.clear()

    assert status == 201
    assert body["status"] == "inserted"
    assert body["ignored"] is False
    assert body["reading_id"] == "r-001"


# ---------------------------------------------------------------------------
# API — duplicate reading_id returns 200 duplicate_ignored
# ---------------------------------------------------------------------------


def test_duplicate_reading_id_returns_200() -> None:
    from app.models.sensor_reading import SensorReading
    plant = _make_plant()
    now = datetime.now(UTC)
    existing = SensorReading(
        id=uuid.uuid4(),
        reading_id="r-001",
        device_id=_DEVICE_ID,
        plant_id=_PLANT_ID,
        measured_at=now,
        temperature_c=22.5,
        humidity_pct=55.0,
        light_lux=3000.0,
        soil_moisture_pct=40.0,
        created_at=now,
    )

    async def _dep():
        sess = _fake_session_factory(plant=plant)
        with patch(
            "app.services.sensor_ingest.SensorRepository.find_by_reading_id",
            new=AsyncMock(return_value=existing),
        ):
            yield sess

    app.dependency_overrides[get_session] = _dep
    try:
        status, body = asyncio.run(_post(_valid_payload()))
    finally:
        app.dependency_overrides.clear()

    assert status == 200
    assert body["status"] == "duplicate_ignored"
    assert body["ignored"] is True


# ---------------------------------------------------------------------------
# API — unknown plant_id returns 404
# ---------------------------------------------------------------------------


def test_unknown_plant_returns_404() -> None:
    async def _dep():
        sess = _fake_session_factory(plant=None)
        yield sess

    app.dependency_overrides[get_session] = _dep
    try:
        status, _ = asyncio.run(_post(_valid_payload()))
    finally:
        app.dependency_overrides.clear()

    assert status == 404


# ---------------------------------------------------------------------------
# API — 422 for invalid payloads
# ---------------------------------------------------------------------------


def test_missing_required_field_returns_422() -> None:
    payload = _valid_payload()
    del payload["reading_id"]
    status, _ = asyncio.run(_post(payload))
    assert status == 422


def test_naive_timestamp_returns_422() -> None:
    status, _ = asyncio.run(
        _post(_valid_payload(measured_at="2026-05-10T10:00:00"))
    )
    assert status == 422


def test_out_of_range_temperature_returns_422() -> None:
    status, _ = asyncio.run(_post(_valid_payload(temperature_c=999.0)))
    assert status == 422


# ---------------------------------------------------------------------------
# Boundary — no forbidden side-effects
# ---------------------------------------------------------------------------


def test_no_snapshot_call_on_ingest() -> None:
    plant = _make_plant()

    async def _dep():
        sess = _fake_session_factory(plant=plant)
        yield sess

    app.dependency_overrides[get_session] = _dep
    snapshot_mock = MagicMock()
    try:
        with (
            patch(
                "app.services.sensor_ingest.SensorRepository.find_by_reading_id",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.services.sensor_ingest.SensorRepository.insert",
                new=AsyncMock(),
            ),
            patch.dict("sys.modules", {"app.services.snapshot_service": snapshot_mock}),
        ):
            asyncio.run(_post(_valid_payload()))
    finally:
        app.dependency_overrides.clear()

    snapshot_mock.assert_not_called()


def test_no_character_update_on_ingest() -> None:
    """Character state must not be modified when ingesting a sensor reading."""
    from app.services import character_state_engine as cse_mod

    plant = _make_plant()

    async def _dep():
        sess = _fake_session_factory(plant=plant)
        yield sess

    app.dependency_overrides[get_session] = _dep
    engine_spy = MagicMock(wraps=cse_mod.CharacterStateEngine)
    try:
        with (
            patch(
                "app.services.sensor_ingest.SensorRepository.find_by_reading_id",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.services.sensor_ingest.SensorRepository.insert",
                new=AsyncMock(),
            ),
            patch.object(cse_mod, "CharacterStateEngine", engine_spy),
        ):
            asyncio.run(_post(_valid_payload()))
    finally:
        app.dependency_overrides.clear()

    engine_spy.assert_not_called()


def test_response_shape() -> None:
    plant = _make_plant()

    async def _dep():
        sess = _fake_session_factory(plant=plant)
        yield sess

    app.dependency_overrides[get_session] = _dep
    try:
        with (
            patch(
                "app.services.sensor_ingest.SensorRepository.find_by_reading_id",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.services.sensor_ingest.SensorRepository.insert",
                new=AsyncMock(),
            ),
        ):
            _, body = asyncio.run(_post(_valid_payload()))
    finally:
        app.dependency_overrides.clear()

    assert set(body.keys()) == {"status", "ignored", "reading_id"}
