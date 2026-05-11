"""RuleEngineResult → Condition mapper — TICKET-008.5.

Pure function: no DB, no LLM, no side-effects. Reads only the
primary_action and reason_codes already computed by RuleEngine.

Priority (first match wins):
  1. water action OR low_soil_moisture reason → "low_soil_moisture"
  2. increase_light action OR low_light reason → "low_light"
  3. humidity/temperature stress           → "unstable_humidity"
  4. anything else                         → "good"
"""

from __future__ import annotations

from app.domain.character_state import Condition
from app.rules.schemas import RuleEngineResult

_HUMIDITY_TEMP_REASON_CODES = frozenset(["low_humidity", "high_humidity", "low_temperature", "high_temperature"])


def map_to_condition(result: RuleEngineResult) -> Condition:
    """Map a RuleEngineResult to the single best-fit Condition code."""
    action = result.primary_action
    codes = set(result.reason_codes)

    if action == "water" or "low_soil_moisture" in codes:
        return "low_soil_moisture"

    if action == "increase_light" or "low_light" in codes:
        return "low_light"

    if action in ("stabilize_humidity", "adjust_temperature") or (codes & _HUMIDITY_TEMP_REASON_CODES):
        return "unstable_humidity"

    return "good"
