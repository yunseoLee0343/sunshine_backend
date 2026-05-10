"""TICKET-013 — Chat Intent Classifier tests (pure, no DB)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.chat_intent import ROUTING_TABLE, ChatIntentRequest


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


def test_request_rejects_blank_question() -> None:
    with pytest.raises(Exception):
        ChatIntentRequest(
            request_id=uuid.uuid4(), user_id=uuid.uuid4(),
            question="   ",
        )


def test_request_rejects_extra_fields() -> None:
    with pytest.raises(Exception):
        ChatIntentRequest(
            request_id=uuid.uuid4(), user_id=uuid.uuid4(),
            question="물은 언제 줘야 해?", bogus="x",
        )


# ---------------------------------------------------------------------------
# Routing table completeness
# ---------------------------------------------------------------------------


def test_routing_table_covers_all_intents() -> None:
    intents = [
        "watering_question", "light_question", "humidity_question",
        "temperature_question", "species_care_question", "pest_reference_question",
        "companion_plant_question", "unknown_question",
    ]
    for intent in intents:
        assert intent in ROUTING_TABLE, f"Missing routing for {intent}"


def test_sensor_intents_require_evidence() -> None:
    for intent in ("watering_question", "light_question", "humidity_question", "temperature_question"):
        assert ROUTING_TABLE[intent].requires_evidence is True


def test_non_sensor_intents_do_not_require_evidence() -> None:
    for intent in ("species_care_question", "pest_reference_question",
                   "companion_plant_question", "unknown_question"):
        assert ROUTING_TABLE[intent].requires_evidence is False


# ---------------------------------------------------------------------------
# Lightweight classifier (Stage 1)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("question,expected", [
    ("물은 얼마나 자주 줘야 하나요?", "watering_question"),
    ("watering schedule for monstera", "watering_question"),
    ("빛이 얼마나 필요해요?", "light_question"),
    ("조도가 어느 정도여야 하나요?", "light_question"),
    ("습도가 너무 낮아요", "humidity_question"),
    ("온도는 몇 도가 적당한가요?", "temperature_question"),
    ("겨울에 관리 방법이 궁금해요", "temperature_question"),
    ("키우는 방법을 알려주세요", "species_care_question"),
    ("진딧물이 생겼어요", "pest_reference_question"),
    ("잎이 노랗게 변해요", "pest_reference_question"),
    ("같이 키울 수 있는 식물이 있나요?", "companion_plant_question"),
])
def test_lightweight_classifier_intent(question: str, expected: str) -> None:
    from app.services.lightweight_intent_classifier import LightweightIntentClassifier
    clf = LightweightIntentClassifier()
    result = clf.classify(question)
    assert result is not None, f"No match for: {question!r}"
    intent, confidence = result
    assert intent == expected, f"Got {intent!r} for: {question!r}"
    assert confidence == 0.95


def test_lightweight_classifier_returns_none_for_ambiguous() -> None:
    from app.services.lightweight_intent_classifier import LightweightIntentClassifier
    clf = LightweightIntentClassifier()
    # Completely off-topic
    assert clf.classify("오늘 날씨가 어때요?") is None


# ---------------------------------------------------------------------------
# Mock LLM classifier (Stage 2)
# ---------------------------------------------------------------------------


def test_mock_classifier_always_returns_result() -> None:
    from app.llm.intent_classifier_mock import MockIntentClassifier
    clf = MockIntentClassifier()
    intent, confidence = clf.classify("아무말이나")
    assert isinstance(intent, str)
    assert 0.0 < confidence <= 1.0


def test_mock_classifier_fallback_is_unknown() -> None:
    from app.llm.intent_classifier_mock import MockIntentClassifier
    clf = MockIntentClassifier()
    intent, confidence = clf.classify("오늘 날씨가 어때요?")
    assert intent == "unknown_question"
    assert confidence == 0.50


def test_mock_classifier_secondary_match() -> None:
    from app.llm.intent_classifier_mock import MockIntentClassifier
    clf = MockIntentClassifier()
    # "물" alone should be caught by secondary pattern
    intent, confidence = clf.classify("물이 너무 많아요")
    assert intent == "watering_question"
    assert confidence == 0.70


# ---------------------------------------------------------------------------
# Hybrid classifier
# ---------------------------------------------------------------------------


def test_hybrid_uses_rule_stage_when_pattern_matches() -> None:
    from app.services.chat_intent_classifier import ChatIntentClassifier
    clf = ChatIntentClassifier()
    intent, confidence, stage = clf.classify("물은 언제 줘야 해?")
    assert stage == "rule"
    assert confidence == 0.95
    assert intent == "watering_question"


def test_hybrid_falls_back_to_llm_stage() -> None:
    from app.services.chat_intent_classifier import ChatIntentClassifier
    clf = ChatIntentClassifier()
    # Deliberately ambiguous — Stage 1 won't match
    intent, confidence, stage = clf.classify("오늘 날씨가 어때요?")
    assert stage == "llm"
    assert confidence < 0.95


def test_hybrid_no_external_import() -> None:
    import app.services.chat_intent_classifier as mod
    src = open(mod.__file__, encoding="utf-8").read()
    for forbidden in ("openai", "anthropic", "requests", "httpx"):
        assert forbidden not in src


# ---------------------------------------------------------------------------
# Repository idempotency (mocked session)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_by_request_id_returns_none_when_absent() -> None:
    from app.repositories.chat_intent_repository import ChatIntentRepository

    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    repo = ChatIntentRepository(session)
    result = await repo.find_by_request_id(uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_find_by_request_id_returns_cached_result() -> None:
    from app.models.chat_request import ChatRequest
    from app.repositories.chat_intent_repository import ChatIntentRepository

    rid = uuid.uuid4()
    fake_row = MagicMock(spec=ChatRequest)
    fake_row.id = rid
    fake_row.status = "watering_question"
    fake_row.created_at = datetime(2026, 5, 10, tzinfo=UTC)

    session = AsyncMock()
    session.get = AsyncMock(return_value=fake_row)
    session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))

    repo = ChatIntentRepository(session)
    result = await repo.find_by_request_id(rid)
    assert result is not None
    assert result.intent == "watering_question"
    assert result.request_id == rid


@pytest.mark.asyncio
async def test_save_creates_chat_request_row() -> None:
    from app.repositories.chat_intent_repository import ChatIntentRepository

    session = AsyncMock()
    session.add = MagicMock()          # add() is synchronous
    session.flush = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))

    repo = ChatIntentRepository(session)
    result = await repo.save(
        request_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        plant_id=None,
        question="물 언제 줘요?",
        intent="watering_question",
        confidence=0.95,
        stage="rule",
    )
    session.add.assert_called()
    assert result.intent == "watering_question"
    assert result.stage == "rule"
    assert result.selected_rule_modules == ["watering"]
    assert result.requires_evidence is True


@pytest.mark.asyncio
async def test_save_llm_stage_creates_llm_run_row() -> None:
    from app.repositories.chat_intent_repository import ChatIntentRepository

    session = AsyncMock()
    session.add = MagicMock()          # add() is synchronous
    session.flush = AsyncMock()

    repo = ChatIntentRepository(session)
    await repo.save(
        request_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        plant_id=None,
        question="아무 질문",
        intent="unknown_question",
        confidence=0.50,
        stage="llm",
    )
    # Two .add() calls: ChatRequest + LlmRun
    assert session.add.call_count == 2
