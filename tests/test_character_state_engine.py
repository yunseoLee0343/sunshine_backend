"""TICKET-004 — CharacterStateEngine unit tests.

Verifies the deterministic 1:1 mapping between plant ``condition`` codes and
``CharacterState``, free-form rejection, and absence of randomness or
time-dependence.
"""

import pytest

from app.domain.character_state import CharacterState
from app.services.character_state_engine import (
    CharacterStateEngine,
    UnknownConditionError,
)

# ---------------------------------------------------------------------------
# Required mappings (§7)
# ---------------------------------------------------------------------------

EXPECTED = {
    "good": ("happy", "smile", "none", "good", "상태가 좋아 보여요."),
    "low_soil_moisture": (
        "thirsty",
        "droop",
        "water",
        "low_soil_moisture",
        "목이 말라 보여요.",
    ),
    "low_light": (
        "sleepy",
        "normal",
        "move_to_brighter_place",
        "low_light",
        "빛이 조금 부족해 보여요.",
    ),
    "unstable_humidity": (
        "stressed",
        "sweat",
        "stabilize_humidity",
        "unstable_humidity",
        "습도 변화가 커서 스트레스를 받은 것 같아요.",
    ),
    "after_watering": (
        "happy",
        "smile",
        "none",
        "after_watering",
        "물을 마시고 기분이 좋아졌어요.",
    ),
    "onboarding_created": (
        "neutral",
        "normal",
        "none",
        "onboarding_created",
        "새 식물이 등록되었어요.",
    ),
}


@pytest.mark.parametrize("condition,expected", list(EXPECTED.items()))
def test_required_mapping(condition, expected) -> None:
    mood, expression, primary_action, reason_code, status_message = expected
    state = CharacterStateEngine().map(condition)
    assert isinstance(state, CharacterState)
    assert state.mood == mood
    assert state.expression == expression
    assert state.primary_action == primary_action
    assert state.reason_code == reason_code
    assert state.status_message == status_message


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("condition", list(EXPECTED.keys()))
def test_same_condition_same_output(condition) -> None:
    a = CharacterStateEngine().map(condition).model_dump()
    b = CharacterStateEngine().map(condition).model_dump()
    assert a == b


def test_returned_state_can_be_safely_mutated() -> None:
    """The engine must not share mutable references across calls."""
    a = CharacterStateEngine().map("good")
    b = CharacterStateEngine().map("good")
    assert a is not b
    # Dump-equality preserves determinism even after independent objects exist.
    assert a.model_dump() == b.model_dump()


# ---------------------------------------------------------------------------
# Free-form / unknown rejection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bogus",
    [
        "make_it_super_cute_by_llm",
        "happy",
        "MOOD_HAPPY",
        "",
        "  good  ",
        "good ",
        "GOOD",
    ],
)
def test_unknown_condition_rejected(bogus) -> None:
    with pytest.raises(UnknownConditionError):
        CharacterStateEngine().map(bogus)


# ---------------------------------------------------------------------------
# Status message templates
# ---------------------------------------------------------------------------


def test_status_messages_come_from_template_set() -> None:
    """All produced status_messages must equal the documented strings."""
    expected_messages = {row[4] for row in EXPECTED.values()}
    actual_messages = {
        CharacterStateEngine().map(c).status_message for c in EXPECTED.keys()
    }
    assert actual_messages == expected_messages


# ---------------------------------------------------------------------------
# No mood/expression passthrough
# ---------------------------------------------------------------------------


def test_engine_signature_only_takes_condition() -> None:
    """Sanity: the engine's only mapping input is the condition string."""
    import inspect

    sig = inspect.signature(CharacterStateEngine.map)
    # self + condition only.
    assert list(sig.parameters.keys()) == ["self", "condition"]
