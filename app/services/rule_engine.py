"""RuleEngine — TICKET-008.

Aggregates results from the four pure-function rules:
  watering · light · humidity · temperature

Aggregation rules:
  - care_status: any needs_action → needs_action; else any watch → watch;
    else all good → good; all insufficient_data → insufficient_data.
  - severity: highest across all rules (high > medium > low > none).
  - primary_action: water has top priority; then needs_action actions in
    declaration order; then watch; else none.

No LLM, no DB, no side-effects. Pure aggregation of RuleResult objects.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import UTC, datetime

from app.rules import humidity, light, temperature, watering
from app.rules.schemas import RuleEngineResult
from app.rules.types import (
    CareStatus,
    LatestSnapshot,
    PrimaryAction,
    RecentCareLog,
    RuleResult,
    Severity,
    SpeciesThresholds,
    severity_max,
)

# Action priority: water first, then other actions, then watch, then none.
_ACTION_PRIORITY: list[PrimaryAction] = [
    "water",
    "increase_light",
    "stabilize_humidity",
    "adjust_temperature",
    "watch",
    "none",
]


def _pick_action(results: list[RuleResult]) -> PrimaryAction:
    candidates = [r.action for r in results if r.action != "none"]
    for preferred in _ACTION_PRIORITY:
        if preferred in candidates:
            return preferred
    return "none"


def _aggregate_status(results: list[RuleResult]) -> CareStatus:
    statuses: set[CareStatus] = {r.care_status for r in results}
    if "needs_action" in statuses:
        return "needs_action"
    if "watch" in statuses:
        return "watch"
    if "good" in statuses:
        return "good"
    return "insufficient_data"


def _aggregate_severity(results: list[RuleResult]) -> Severity:
    sev: Severity = "none"
    for r in results:
        sev = severity_max(sev, r.severity)
    return sev


class RuleEngine:
    """Pure deterministic rule aggregator."""

    def evaluate(
        self,
        plant_id: uuid.UUID,
        thresholds: SpeciesThresholds,
        snapshot: LatestSnapshot,
        care_logs: list[RecentCareLog],
        *,
        now: datetime | None = None,
    ) -> RuleEngineResult:
        evaluated_at = now or datetime.now(UTC)

        results: list[RuleResult] = [
            watering.evaluate(thresholds, snapshot, care_logs),
            light.evaluate(thresholds, snapshot, care_logs),
            humidity.evaluate(thresholds, snapshot, care_logs),
            temperature.evaluate(thresholds, snapshot, care_logs),
        ]

        care_status = _aggregate_status(results)
        severity = _aggregate_severity(results)
        primary_action = _pick_action(results)

        all_reason_codes: list[str] = []
        all_evidence: dict[str, object] = {}
        for r in results:
            for code in r.reason_codes:
                if code not in all_reason_codes:
                    all_reason_codes.append(code)
            for k, v in r.evidence_facts.items():
                all_evidence[f"{r.rule}.{k}"] = v

        return RuleEngineResult(
            plant_id=plant_id,
            evaluated_at=evaluated_at,
            care_status=care_status,
            primary_action=primary_action,
            severity=severity,
            reason_codes=all_reason_codes,
            evidence_facts=all_evidence,
            rule_results=[asdict(r) for r in results],
        )
