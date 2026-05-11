"""Shared types for the Rule Engine — TICKET-008.

All types are pure dataclasses / Pydantic models with no DB or I/O dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

CareStatus = Literal["good", "needs_action", "watch", "insufficient_data"]
Severity = Literal["none", "low", "medium", "high"]
PrimaryAction = Literal[
    "none",
    "water",
    "increase_light",
    "stabilize_humidity",
    "adjust_temperature",
    "watch",
]

_SEVERITY_ORDER: dict[Severity, int] = {
    "none": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
}


def severity_max(a: Severity, b: Severity) -> Severity:
    return a if _SEVERITY_ORDER[a] >= _SEVERITY_ORDER[b] else b


# ---------------------------------------------------------------------------
# Rule input DTOs  (pure data, no ORM)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SpeciesThresholds:
    """Thresholds read from species_profiles. Any field may be None."""

    water_min_pct: Decimal | None = None
    water_max_pct: Decimal | None = None
    light_min_lux: Decimal | None = None
    light_max_lux: Decimal | None = None
    humidity_min_pct: Decimal | None = None
    humidity_max_pct: Decimal | None = None
    temperature_min_c: Decimal | None = None
    temperature_max_c: Decimal | None = None


@dataclass(frozen=True)
class LatestSnapshot:
    """Metric averages from the latest environment snapshot. None = missing."""

    soil_moisture_avg_pct: float | None = None
    light_avg_lux: float | None = None
    humidity_avg_pct: float | None = None
    temperature_avg_c: float | None = None


@dataclass(frozen=True)
class RecentCareLog:
    """A single care-log entry relevant to rule evaluation."""

    action_type: str  # e.g. "water", "fertilise", …
    hours_ago: float  # positive; 0.0 = acted_at == now


# ---------------------------------------------------------------------------
# Rule result
# ---------------------------------------------------------------------------


@dataclass
class RuleResult:
    rule: str  # e.g. "watering"
    care_status: CareStatus
    severity: Severity
    action: PrimaryAction
    reason_codes: list[str] = field(default_factory=list)
    evidence_facts: dict[str, object] = field(default_factory=dict)
