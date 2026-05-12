"""S-001 — SensorReadingRequest schema tests."""
import math
import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.sensor_readings import SensorReadingRequest

_TS = "2026-05-07T15:30:00+09:00"
_PLANT = str(uuid.uuid4())


def _req(**overrides) -> dict:
    base = {
        "reading_id": "r-001",
        "device_id": "dev-001",
        "plant_id": _PLANT,
        "measured_at": _TS,
        "temperature_c": 22.0,
        "humidity_pct": 55.0,
        "light_lux": 1000.0,
        "soil_moisture_pct": 40.0,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. Null metrics accepted
# ---------------------------------------------------------------------------


def test_all_metrics_null_accepted() -> None:
    req = SensorReadingRequest.model_validate(
        _req(temperature_c=None, humidity_pct=None, light_lux=None, soil_moisture_pct=None)
    )
    assert req.temperature_c is None
    assert req.humidity_pct is None
    assert req.light_lux is None
    assert req.soil_moisture_pct is None


def test_partial_null_metrics_accepted() -> None:
    req = SensorReadingRequest.model_validate(_req(humidity_pct=None, soil_moisture_pct=None))
    assert req.humidity_pct is None
    assert req.soil_moisture_pct is None
    assert req.temperature_c == 22.0
    assert req.light_lux == 1000.0


def test_null_metrics_omitted_defaults_to_none() -> None:
    d = _req()
    del d["temperature_c"]
    del d["humidity_pct"]
    req = SensorReadingRequest.model_validate(d)
    assert req.temperature_c is None
    assert req.humidity_pct is None


# ---------------------------------------------------------------------------
# 2. NaN / Inf rejected when metric is not null
# ---------------------------------------------------------------------------


def test_nan_temperature_rejected() -> None:
    with pytest.raises(ValidationError, match="temperature_c"):
        SensorReadingRequest.model_validate(_req(temperature_c=math.nan))


def test_inf_humidity_rejected() -> None:
    with pytest.raises(ValidationError, match="humidity_pct"):
        SensorReadingRequest.model_validate(_req(humidity_pct=math.inf))


def test_neg_inf_light_rejected() -> None:
    with pytest.raises(ValidationError, match="light_lux"):
        SensorReadingRequest.model_validate(_req(light_lux=-math.inf))


def test_nan_soil_rejected() -> None:
    with pytest.raises(ValidationError, match="soil_moisture_pct"):
        SensorReadingRequest.model_validate(_req(soil_moisture_pct=math.nan))


def test_null_metrics_not_nan_rejected() -> None:
    """None is NOT treated as NaN — must not raise."""
    req = SensorReadingRequest.model_validate(_req(temperature_c=None))
    assert req.temperature_c is None


# ---------------------------------------------------------------------------
# 3. Range validation still applies to non-null values
# ---------------------------------------------------------------------------


def test_temperature_above_max_rejected() -> None:
    with pytest.raises(ValidationError):
        SensorReadingRequest.model_validate(_req(temperature_c=81.0))


def test_temperature_below_min_rejected() -> None:
    with pytest.raises(ValidationError):
        SensorReadingRequest.model_validate(_req(temperature_c=-41.0))


def test_humidity_above_100_rejected() -> None:
    with pytest.raises(ValidationError):
        SensorReadingRequest.model_validate(_req(humidity_pct=101.0))


def test_light_lux_above_max_rejected() -> None:
    with pytest.raises(ValidationError):
        SensorReadingRequest.model_validate(_req(light_lux=200_001.0))


def test_soil_moisture_negative_rejected() -> None:
    with pytest.raises(ValidationError):
        SensorReadingRequest.model_validate(_req(soil_moisture_pct=-1.0))


def test_boundary_values_accepted() -> None:
    req = SensorReadingRequest.model_validate(
        _req(temperature_c=-40.0, humidity_pct=0.0, light_lux=200_000.0, soil_moisture_pct=100.0)
    )
    assert req.temperature_c == -40.0
    assert req.soil_moisture_pct == 100.0


# ---------------------------------------------------------------------------
# 4. plant_id accepts both UUID strings and external IDs
# ---------------------------------------------------------------------------


def test_plant_id_uuid_string_accepted() -> None:
    req = SensorReadingRequest.model_validate(_req(plant_id=str(uuid.uuid4())))
    assert isinstance(req.plant_id, str)


def test_plant_id_external_string_accepted() -> None:
    req = SensorReadingRequest.model_validate(_req(plant_id="plant-001"))
    assert req.plant_id == "plant-001"
