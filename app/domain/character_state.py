"""CharacterState domain schemas — TICKET-004.

Pure value objects. No DB I/O, no LLM, no Rule Engine, no sensor lookup.
All fields are finite enums or deterministic templates.
"""

from typing import Literal

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Enums (declared as Literal so Pydantic enforces them at the boundary)
# ---------------------------------------------------------------------------

Mood = Literal["happy", "thirsty", "sleepy", "stressed", "neutral"]
Expression = Literal["smile", "droop", "normal", "sweat"]
PrimaryAction = Literal["none", "water", "move_to_brighter_place", "stabilize_humidity"]
ReasonCode = Literal[
    "good",
    "low_soil_moisture",
    "low_light",
    "unstable_humidity",
    "after_watering",
    "onboarding_created",
]
Condition = Literal[
    "good",
    "low_soil_moisture",
    "low_light",
    "unstable_humidity",
    "after_watering",
    "onboarding_created",
]
ConditionSource = Literal[
    "onboarding",
    "manual_test",
    "future_snapshot",
    "future_care_log",
]


class CharacterState(BaseModel):
    """Deterministic companion character state."""

    mood: Mood
    expression: Expression
    status_message: str
    primary_action: PrimaryAction
    reason_code: ReasonCode
