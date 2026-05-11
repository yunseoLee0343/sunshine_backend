"""Watering rule — TICKET-008.

Logic:
  - No soil_moisture reading or no threshold → insufficient_data.
  - Soil moisture < water_min_pct AND no watering in last 6 h → needs_action / water.
  - Soil moisture < water_min_pct BUT watered in last 6 h → watch (action suppressed).
  - Otherwise → good.

No LLM, no DB access, no side-effects.
"""

from __future__ import annotations

from app.rules.types import (
    LatestSnapshot,
    RecentCareLog,
    RuleResult,
    SpeciesThresholds,
)

_WATERING_WINDOW_H = 6.0
_WATERING_ACTION_TYPE = "water"


def evaluate(
    thresholds: SpeciesThresholds,
    snapshot: LatestSnapshot,
    care_logs: list[RecentCareLog],
) -> RuleResult:
    soil = snapshot.soil_moisture_avg_pct
    water_min = float(thresholds.water_min_pct) if thresholds.water_min_pct is not None else None

    if soil is None or water_min is None:
        return RuleResult(
            rule="watering",
            care_status="insufficient_data",
            severity="none",
            action="none",
            reason_codes=["insufficient_data"],
            evidence_facts={"soil_moisture_avg_pct": soil, "water_min_pct": water_min},
        )

    recently_watered = any(
        log.action_type == _WATERING_ACTION_TYPE and log.hours_ago <= _WATERING_WINDOW_H for log in care_logs
    )

    if soil < water_min:
        if recently_watered:
            return RuleResult(
                rule="watering",
                care_status="watch",
                severity="low",
                action="watch",
                reason_codes=["low_soil_moisture", "recently_watered"],
                evidence_facts={
                    "soil_moisture_avg_pct": soil,
                    "water_min_pct": water_min,
                    "recently_watered": True,
                },
            )
        return RuleResult(
            rule="watering",
            care_status="needs_action",
            severity="high",
            action="water",
            reason_codes=["low_soil_moisture"],
            evidence_facts={
                "soil_moisture_avg_pct": soil,
                "water_min_pct": water_min,
                "recently_watered": False,
            },
        )

    return RuleResult(
        rule="watering",
        care_status="good",
        severity="none",
        action="none",
        reason_codes=["good"],
        evidence_facts={"soil_moisture_avg_pct": soil, "water_min_pct": water_min},
    )
