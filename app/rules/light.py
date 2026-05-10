"""Light rule — TICKET-008.

Logic:
  - No light reading or no threshold → insufficient_data.
  - light < light_min → needs_action / increase_light (medium severity).
  - light > light_max (if set) → watch / none (low severity).
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
    care_logs: list[RecentCareLog],  # noqa: ARG001 — not used for light
) -> RuleResult:
    lux = snapshot.light_avg_lux
    light_min = (
        float(thresholds.light_min_lux) if thresholds.light_min_lux is not None else None
    )
    light_max = (
        float(thresholds.light_max_lux) if thresholds.light_max_lux is not None else None
    )

    if lux is None or light_min is None:
        return RuleResult(
            rule="light",
            care_status="insufficient_data",
            severity="none",
            action="none",
            reason_codes=["insufficient_data"],
            evidence_facts={"light_avg_lux": lux, "light_min_lux": light_min},
        )

    if lux < light_min:
        return RuleResult(
            rule="light",
            care_status="needs_action",
            severity="medium",
            action="increase_light",
            reason_codes=["low_light"],
            evidence_facts={"light_avg_lux": lux, "light_min_lux": light_min},
        )

    if light_max is not None and lux > light_max:
        return RuleResult(
            rule="light",
            care_status="watch",
            severity="low",
            action="none",
            reason_codes=["excess_light"],
            evidence_facts={"light_avg_lux": lux, "light_max_lux": light_max},
        )

    return RuleResult(
        rule="light",
        care_status="good",
        severity="none",
        action="none",
        reason_codes=["good"],
        evidence_facts={"light_avg_lux": lux},
    )
