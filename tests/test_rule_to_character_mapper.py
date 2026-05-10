"""TICKET-008.5 — rule_to_character_mapper pure-function tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.rules.schemas import RuleEngineResult
from app.services.rule_to_character_mapper import map_to_condition

_PLANT = uuid.uuid4()
_NOW = datetime(2026, 5, 10, 12, 0, 0, tzinfo=UTC)


def _result(
    *,
    care_status: str = "good",
    primary_action: str = "none",
    severity: str = "none",
    reason_codes: list[str] | None = None,
) -> RuleEngineResult:
    return RuleEngineResult(
        plant_id=_PLANT,
        evaluated_at=_NOW,
        care_status=care_status,  # type: ignore[arg-type]
        primary_action=primary_action,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        reason_codes=reason_codes or [],
        evidence_facts={},
        rule_results=[],
    )


# ---------------------------------------------------------------------------
# Priority 1: water / low_soil_moisture
# ---------------------------------------------------------------------------


def test_water_action_maps_to_low_soil_moisture() -> None:
    r = _result(care_status="needs_action", primary_action="water", severity="high",
                reason_codes=["low_soil_moisture"])
    assert map_to_condition(r) == "low_soil_moisture"


def test_low_soil_moisture_reason_code_without_action() -> None:
    r = _result(care_status="watch", primary_action="watch",
                reason_codes=["low_soil_moisture", "recently_watered"])
    assert map_to_condition(r) == "low_soil_moisture"


def test_water_action_takes_priority_over_light() -> None:
    r = _result(care_status="needs_action", primary_action="water", severity="high",
                reason_codes=["low_soil_moisture", "low_light"])
    assert map_to_condition(r) == "low_soil_moisture"


# ---------------------------------------------------------------------------
# Priority 2: increase_light / low_light
# ---------------------------------------------------------------------------


def test_increase_light_action_maps_to_low_light() -> None:
    r = _result(care_status="needs_action", primary_action="increase_light",
                severity="medium", reason_codes=["low_light"])
    assert map_to_condition(r) == "low_light"


def test_low_light_reason_code_maps_to_low_light() -> None:
    r = _result(care_status="needs_action", primary_action="increase_light",
                reason_codes=["low_light"])
    assert map_to_condition(r) == "low_light"


def test_light_takes_priority_over_humidity() -> None:
    r = _result(care_status="needs_action", primary_action="increase_light",
                reason_codes=["low_light", "low_humidity"])
    assert map_to_condition(r) == "low_light"


# ---------------------------------------------------------------------------
# Priority 3: humidity / temperature stress → unstable_humidity
# ---------------------------------------------------------------------------


def test_stabilize_humidity_action_maps_to_unstable_humidity() -> None:
    r = _result(care_status="needs_action", primary_action="stabilize_humidity",
                reason_codes=["low_humidity"])
    assert map_to_condition(r) == "unstable_humidity"


def test_adjust_temperature_action_maps_to_unstable_humidity() -> None:
    r = _result(care_status="needs_action", primary_action="adjust_temperature",
                reason_codes=["low_temperature"])
    assert map_to_condition(r) == "unstable_humidity"


def test_high_humidity_reason_maps_to_unstable_humidity() -> None:
    r = _result(care_status="needs_action", primary_action="stabilize_humidity",
                reason_codes=["high_humidity"])
    assert map_to_condition(r) == "unstable_humidity"


def test_high_temperature_reason_maps_to_unstable_humidity() -> None:
    r = _result(care_status="needs_action", primary_action="adjust_temperature",
                reason_codes=["high_temperature"])
    assert map_to_condition(r) == "unstable_humidity"


# ---------------------------------------------------------------------------
# Priority 4: good / fallback
# ---------------------------------------------------------------------------


def test_all_good_maps_to_good() -> None:
    r = _result(care_status="good", primary_action="none")
    assert map_to_condition(r) == "good"


def test_insufficient_data_maps_to_good() -> None:
    r = _result(care_status="insufficient_data", primary_action="none")
    assert map_to_condition(r) == "good"


def test_watch_without_known_reason_maps_to_good() -> None:
    r = _result(care_status="watch", primary_action="watch",
                reason_codes=["recently_watered"])
    assert map_to_condition(r) == "good"


# ---------------------------------------------------------------------------
# Mapper is pure / deterministic
# ---------------------------------------------------------------------------


def test_mapper_is_deterministic() -> None:
    r = _result(care_status="needs_action", primary_action="water",
                reason_codes=["low_soil_moisture"])
    assert map_to_condition(r) == map_to_condition(r)
