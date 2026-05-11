"""Temperature rule — TICKET-008.

Logic:
  - No temperature reading or no threshold → insufficient_data.
  - temp < temperature_min → needs_action / adjust_temperature (medium severity).
  - temp > temperature_max (if set) → needs_action / adjust_temperature (medium severity).
  - Otherwise → good.
"""

from __future__ import annotations

from app.rules.types import (
    LatestSnapshot,
    RecentCareLog,
    RuleResult,
    SpeciesThresholds,
)


def evaluate(
    thresholds: SpeciesThresholds,
    snapshot: LatestSnapshot,
    care_logs: list[RecentCareLog],  # noqa: ARG001
) -> RuleResult:
    temp = snapshot.temperature_avg_c
    temp_min = float(thresholds.temperature_min_c) if thresholds.temperature_min_c is not None else None
    temp_max = float(thresholds.temperature_max_c) if thresholds.temperature_max_c is not None else None

    if temp is None or temp_min is None:
        return RuleResult(
            rule="temperature",
            care_status="insufficient_data",
            severity="none",
            action="none",
            reason_codes=["insufficient_data"],
            evidence_facts={"temperature_avg_c": temp, "temperature_min_c": temp_min},
        )

    if temp < temp_min:
        return RuleResult(
            rule="temperature",
            care_status="needs_action",
            severity="medium",
            action="adjust_temperature",
            reason_codes=["low_temperature"],
            evidence_facts={"temperature_avg_c": temp, "temperature_min_c": temp_min},
        )

    if temp_max is not None and temp > temp_max:
        return RuleResult(
            rule="temperature",
            care_status="needs_action",
            severity="medium",
            action="adjust_temperature",
            reason_codes=["high_temperature"],
            evidence_facts={"temperature_avg_c": temp, "temperature_max_c": temp_max},
        )

    return RuleResult(
        rule="temperature",
        care_status="good",
        severity="none",
        action="none",
        reason_codes=["good"],
        evidence_facts={"temperature_avg_c": temp},
    )
