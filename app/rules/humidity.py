"""Humidity rule — TICKET-008.

Logic:
  - No humidity reading or no threshold → insufficient_data.
  - humidity < humidity_min → needs_action / stabilize_humidity (medium severity).
  - humidity > humidity_max (if set) → needs_action / stabilize_humidity (low severity).
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
    humi = snapshot.humidity_avg_pct
    humi_min = float(thresholds.humidity_min_pct) if thresholds.humidity_min_pct is not None else None
    humi_max = float(thresholds.humidity_max_pct) if thresholds.humidity_max_pct is not None else None

    if humi is None or humi_min is None:
        return RuleResult(
            rule="humidity",
            care_status="insufficient_data",
            severity="none",
            action="none",
            reason_codes=["insufficient_data"],
            evidence_facts={"humidity_avg_pct": humi, "humidity_min_pct": humi_min},
        )

    if humi < humi_min:
        return RuleResult(
            rule="humidity",
            care_status="needs_action",
            severity="medium",
            action="stabilize_humidity",
            reason_codes=["low_humidity"],
            evidence_facts={"humidity_avg_pct": humi, "humidity_min_pct": humi_min},
        )

    if humi_max is not None and humi > humi_max:
        return RuleResult(
            rule="humidity",
            care_status="needs_action",
            severity="low",
            action="stabilize_humidity",
            reason_codes=["high_humidity"],
            evidence_facts={"humidity_avg_pct": humi, "humidity_max_pct": humi_max},
        )

    return RuleResult(
        rule="humidity",
        care_status="good",
        severity="none",
        action="none",
        reason_codes=["good"],
        evidence_facts={"humidity_avg_pct": humi},
    )
