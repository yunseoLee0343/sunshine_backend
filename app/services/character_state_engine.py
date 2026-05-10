"""CharacterStateEngine — TICKET-004.

Pure deterministic mapping from a finite set of plant ``condition`` codes to
a ``CharacterState``. No DB access, no LLM, no Rule Engine, no sensor lookup,
no time/random influence. The same input always produces the same output.
"""

from app.domain.character_state import CharacterState, Condition

_MAPPING: dict[Condition, CharacterState] = {
    "good": CharacterState(
        mood="happy",
        expression="smile",
        status_message="상태가 좋아 보여요.",
        primary_action="none",
        reason_code="good",
    ),
    "low_soil_moisture": CharacterState(
        mood="thirsty",
        expression="droop",
        status_message="목이 말라 보여요.",
        primary_action="water",
        reason_code="low_soil_moisture",
    ),
    "low_light": CharacterState(
        mood="sleepy",
        expression="normal",
        status_message="빛이 조금 부족해 보여요.",
        primary_action="move_to_brighter_place",
        reason_code="low_light",
    ),
    "unstable_humidity": CharacterState(
        mood="stressed",
        expression="sweat",
        status_message="습도 변화가 커서 스트레스를 받은 것 같아요.",
        primary_action="stabilize_humidity",
        reason_code="unstable_humidity",
    ),
    "after_watering": CharacterState(
        mood="happy",
        expression="smile",
        status_message="물을 마시고 기분이 좋아졌어요.",
        primary_action="none",
        reason_code="after_watering",
    ),
    "onboarding_created": CharacterState(
        mood="neutral",
        expression="normal",
        status_message="새 식물이 등록되었어요.",
        primary_action="none",
        reason_code="onboarding_created",
    ),
}


class UnknownConditionError(ValueError):
    """Raised when a caller supplies an unsupported condition code."""


class CharacterStateEngine:
    """Maps a finite ``condition`` code to a deterministic ``CharacterState``."""

    def map(self, condition: str) -> CharacterState:
        state = _MAPPING.get(condition)  # type: ignore[arg-type]
        if state is None:
            raise UnknownConditionError(f"unknown condition: {condition!r}")
        # Return a copy so callers cannot mutate the shared template.
        return state.model_copy()
