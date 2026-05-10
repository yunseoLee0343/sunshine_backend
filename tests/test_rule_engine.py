"""TICKET-008 — Rule Engine tests (pure, no DB)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.rules import humidity, light, temperature, watering
from app.rules.types import (
    LatestSnapshot,
    RecentCareLog,
    RuleResult,
    SpeciesThresholds,
)
from app.services.rule_engine import RuleEngine

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 5, 10, 12, 0, 0, tzinfo=UTC)
_PLANT = uuid.uuid4()

_THRESH = SpeciesThresholds(
    water_min_pct=Decimal("30"),
    water_max_pct=Decimal("80"),
    light_min_lux=Decimal("1000"),
    light_max_lux=Decimal("50000"),
    humidity_min_pct=Decimal("40"),
    humidity_max_pct=Decimal("80"),
    temperature_min_c=Decimal("15"),
    temperature_max_c=Decimal("30"),
)

_GOOD_SNAP = LatestSnapshot(
    soil_moisture_avg_pct=50.0,
    light_avg_lux=5000.0,
    humidity_avg_pct=60.0,
    temperature_avg_c=22.0,
)

_NO_LOGS: list[RecentCareLog] = []


# ===========================================================================
# Watering rule
# ===========================================================================


def test_watering_good() -> None:
    r = watering.evaluate(_THRESH, _GOOD_SNAP, _NO_LOGS)
    assert r.care_status == "good"
    assert r.action == "none"


def test_watering_low_moisture_needs_action() -> None:
    snap = LatestSnapshot(soil_moisture_avg_pct=10.0)
    r = watering.evaluate(_THRESH, snap, _NO_LOGS)
    assert r.care_status == "needs_action"
    assert r.action == "water"
    assert r.severity == "high"
    assert "low_soil_moisture" in r.reason_codes


def test_watering_low_moisture_but_recently_watered_gives_watch() -> None:
    snap = LatestSnapshot(soil_moisture_avg_pct=10.0)
    logs = [RecentCareLog(action_type="water", hours_ago=3.0)]
    r = watering.evaluate(_THRESH, snap, logs)
    assert r.care_status == "watch"
    assert r.action == "watch"
    assert "recently_watered" in r.reason_codes


def test_watering_watered_7h_ago_does_not_suppress() -> None:
    snap = LatestSnapshot(soil_moisture_avg_pct=10.0)
    logs = [RecentCareLog(action_type="water", hours_ago=7.0)]
    r = watering.evaluate(_THRESH, snap, logs)
    assert r.care_status == "needs_action"
    assert r.action == "water"


def test_watering_missing_soil_data_gives_insufficient_data() -> None:
    snap = LatestSnapshot(soil_moisture_avg_pct=None)
    r = watering.evaluate(_THRESH, snap, _NO_LOGS)
    assert r.care_status == "insufficient_data"


def test_watering_missing_threshold_gives_insufficient_data() -> None:
    thresh = SpeciesThresholds()
    r = watering.evaluate(thresh, _GOOD_SNAP, _NO_LOGS)
    assert r.care_status == "insufficient_data"


# ===========================================================================
# Light rule
# ===========================================================================


def test_light_good() -> None:
    r = light.evaluate(_THRESH, _GOOD_SNAP, _NO_LOGS)
    assert r.care_status == "good"


def test_light_low_needs_action() -> None:
    snap = LatestSnapshot(light_avg_lux=200.0)
    r = light.evaluate(_THRESH, snap, _NO_LOGS)
    assert r.care_status == "needs_action"
    assert r.action == "increase_light"
    assert r.severity == "medium"


def test_light_excess_gives_watch() -> None:
    snap = LatestSnapshot(light_avg_lux=60000.0)
    r = light.evaluate(_THRESH, snap, _NO_LOGS)
    assert r.care_status == "watch"


def test_light_missing_data() -> None:
    snap = LatestSnapshot(light_avg_lux=None)
    r = light.evaluate(_THRESH, snap, _NO_LOGS)
    assert r.care_status == "insufficient_data"


# ===========================================================================
# Humidity rule
# ===========================================================================


def test_humidity_good() -> None:
    r = humidity.evaluate(_THRESH, _GOOD_SNAP, _NO_LOGS)
    assert r.care_status == "good"


def test_humidity_low_needs_action() -> None:
    snap = LatestSnapshot(humidity_avg_pct=20.0)
    r = humidity.evaluate(_THRESH, snap, _NO_LOGS)
    assert r.care_status == "needs_action"
    assert r.action == "stabilize_humidity"


def test_humidity_high_needs_action() -> None:
    snap = LatestSnapshot(humidity_avg_pct=90.0)
    r = humidity.evaluate(_THRESH, snap, _NO_LOGS)
    assert r.care_status == "needs_action"
    assert r.action == "stabilize_humidity"


def test_humidity_missing_data() -> None:
    snap = LatestSnapshot(humidity_avg_pct=None)
    r = humidity.evaluate(_THRESH, snap, _NO_LOGS)
    assert r.care_status == "insufficient_data"


# ===========================================================================
# Temperature rule
# ===========================================================================


def test_temperature_good() -> None:
    r = temperature.evaluate(_THRESH, _GOOD_SNAP, _NO_LOGS)
    assert r.care_status == "good"


def test_temperature_low_needs_action() -> None:
    snap = LatestSnapshot(temperature_avg_c=5.0)
    r = temperature.evaluate(_THRESH, snap, _NO_LOGS)
    assert r.care_status == "needs_action"
    assert r.action == "adjust_temperature"
    assert r.severity == "medium"


def test_temperature_high_needs_action() -> None:
    snap = LatestSnapshot(temperature_avg_c=35.0)
    r = temperature.evaluate(_THRESH, snap, _NO_LOGS)
    assert r.care_status == "needs_action"
    assert r.action == "adjust_temperature"


def test_temperature_missing_data() -> None:
    snap = LatestSnapshot(temperature_avg_c=None)
    r = temperature.evaluate(_THRESH, snap, _NO_LOGS)
    assert r.care_status == "insufficient_data"


# ===========================================================================
# RuleEngine aggregation
# ===========================================================================


def test_engine_all_good() -> None:
    result = RuleEngine().evaluate(_PLANT, _THRESH, _GOOD_SNAP, _NO_LOGS, now=_NOW)
    assert result.care_status == "good"
    assert result.severity == "none"
    assert result.primary_action == "none"


def test_engine_water_takes_top_priority() -> None:
    """water beats increase_light even if both fire."""
    snap = LatestSnapshot(
        soil_moisture_avg_pct=5.0,   # low → water
        light_avg_lux=100.0,          # low → increase_light
        humidity_avg_pct=60.0,
        temperature_avg_c=22.0,
    )
    result = RuleEngine().evaluate(_PLANT, _THRESH, snap, _NO_LOGS, now=_NOW)
    assert result.primary_action == "water"
    assert result.care_status == "needs_action"


def test_engine_any_needs_action_wins_status() -> None:
    snap = LatestSnapshot(
        soil_moisture_avg_pct=50.0,
        light_avg_lux=100.0,          # triggers needs_action
        humidity_avg_pct=60.0,
        temperature_avg_c=22.0,
    )
    result = RuleEngine().evaluate(_PLANT, _THRESH, snap, _NO_LOGS, now=_NOW)
    assert result.care_status == "needs_action"


def test_engine_highest_severity_adopted() -> None:
    # watering → high, light → medium: engine picks high
    snap = LatestSnapshot(
        soil_moisture_avg_pct=5.0,
        light_avg_lux=100.0,
        humidity_avg_pct=60.0,
        temperature_avg_c=22.0,
    )
    result = RuleEngine().evaluate(_PLANT, _THRESH, snap, _NO_LOGS, now=_NOW)
    assert result.severity == "high"


def test_engine_all_insufficient_data() -> None:
    snap = LatestSnapshot()   # all None
    thresh = SpeciesThresholds()  # all None
    result = RuleEngine().evaluate(_PLANT, thresh, snap, _NO_LOGS, now=_NOW)
    assert result.care_status == "insufficient_data"


def test_engine_reason_codes_merged() -> None:
    snap = LatestSnapshot(
        soil_moisture_avg_pct=5.0,
        light_avg_lux=100.0,
        humidity_avg_pct=60.0,
        temperature_avg_c=22.0,
    )
    result = RuleEngine().evaluate(_PLANT, _THRESH, snap, _NO_LOGS, now=_NOW)
    assert "low_soil_moisture" in result.reason_codes
    assert "low_light" in result.reason_codes


def test_engine_evidence_facts_namespaced() -> None:
    result = RuleEngine().evaluate(_PLANT, _THRESH, _GOOD_SNAP, _NO_LOGS, now=_NOW)
    assert any(k.startswith("watering.") for k in result.evidence_facts)
    assert any(k.startswith("light.") for k in result.evidence_facts)


def test_engine_rule_results_has_four_entries() -> None:
    result = RuleEngine().evaluate(_PLANT, _THRESH, _GOOD_SNAP, _NO_LOGS, now=_NOW)
    assert len(result.rule_results) == 4


def test_engine_deterministic() -> None:
    a = RuleEngine().evaluate(_PLANT, _THRESH, _GOOD_SNAP, _NO_LOGS, now=_NOW)
    b = RuleEngine().evaluate(_PLANT, _THRESH, _GOOD_SNAP, _NO_LOGS, now=_NOW)
    assert a.model_dump() == b.model_dump()


def test_engine_no_llm_import() -> None:
    import app.services.rule_engine as mod
    src = open(mod.__file__, encoding="utf-8").read()
    for forbidden in ("openai", "anthropic", "vllm", "langchain"):
        assert forbidden not in src


def test_engine_output_schema_fields() -> None:
    result = RuleEngine().evaluate(_PLANT, _THRESH, _GOOD_SNAP, _NO_LOGS, now=_NOW)
    d = result.model_dump()
    for key in ("plant_id", "evaluated_at", "care_status", "primary_action",
                "severity", "reason_codes", "evidence_facts", "rule_results"):
        assert key in d
