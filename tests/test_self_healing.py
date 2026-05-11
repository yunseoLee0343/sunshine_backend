"""Tests for TICKET-032: AnswerValidator, SelfHealingOrchestrator, MockHealingLLMClient."""

from __future__ import annotations

import uuid
from dataclasses import replace

import pytest

from app.domain.evidence import ForwardContext
from app.llm.mock_healing_client import MockHealingLLMClient
from app.schemas.chat_answer import ParsedAnswer
from app.services.answer_validator import AnswerValidator, ValidationResult, _check_format
from app.services.llm_port import LLMRequest
from app.services.self_healing_orchestrator import (
    MAX_ATTEMPTS,
    SelfHealingOrchestrator,
    _build_correction_prompt,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ctx(**kwargs) -> ForwardContext:
    defaults = dict(
        plant_id="pid",
        user_id="uid",
        question="test question",
        intent="watering_question",
        rag_layers=[],
        character=None,
        snapshot=None,
        recent_care_logs=[],
        rule_evidence_facts={},
        rule_reason_codes=[],
        rule_primary_action="none",
        retrieved_chunks=[],
        source_coverage={},
    )
    defaults.update(kwargs)
    return ForwardContext(**defaults)


def _make_request(system_prompt: str = "normal prompt") -> LLMRequest:
    import hashlib

    ph = hashlib.sha256(system_prompt.encode()).hexdigest()
    return LLMRequest(
        request_id=uuid.uuid4(),
        system_prompt=system_prompt,
        user_turn="물주기 질문",
        prompt_hash=ph,
    )


def _valid_answer(**kwargs) -> ParsedAnswer:
    defaults = dict(
        결론="식물에 물이 필요한 상태입니다.",
        근거="토양 수분 센서 데이터를 기반으로 분석했습니다.",
        행동="오늘 중으로 물을 충분히 주세요.",
        주의="과습 방지를 위해 받침대 물을 제거하세요.",
    )
    defaults.update(kwargs)
    return ParsedAnswer(**defaults)


# ---------------------------------------------------------------------------
# FormatValidator: _check_format
# ---------------------------------------------------------------------------


def test_format_check_passes_all_valid_sections():
    answer = _valid_answer()
    errors = _check_format(answer)
    assert errors == []


def test_format_check_fails_empty_결론():
    answer = _valid_answer(결론="")
    errors = _check_format(answer)
    assert any("결론" in e for e in errors)


def test_format_check_fails_whitespace_only_근거():
    answer = _valid_answer(근거="   ")
    errors = _check_format(answer)
    assert any("근거" in e for e in errors)


def test_format_check_fails_too_short_행동():
    answer = _valid_answer(행동="ok")  # length < _MIN_SECTION_LEN (5)
    errors = _check_format(answer)
    assert any("행동" in e for e in errors)


def test_format_check_fails_empty_주의():
    answer = _valid_answer(주의="")
    errors = _check_format(answer)
    assert any("주의" in e for e in errors)


def test_format_check_fails_multiple_empty_sections():
    answer = _valid_answer(결론="", 행동="")
    errors = _check_format(answer)
    assert len(errors) >= 2


# ---------------------------------------------------------------------------
# AnswerValidator: full validate()
# ---------------------------------------------------------------------------


def test_validator_passes_valid_answer():
    ctx = _make_ctx()
    validator = AnswerValidator()
    result = validator.validate(_valid_answer(), ctx)
    assert result.passed is True
    assert result.errors == []
    assert result.failed_checks == []


def test_validator_fails_empty_section():
    ctx = _make_ctx()
    validator = AnswerValidator()
    result = validator.validate(_valid_answer(결론=""), ctx)
    assert result.passed is False
    assert "format" in result.failed_checks
    assert any("결론" in e for e in result.errors)


def test_validator_result_frozen():
    result = ValidationResult(passed=True, errors=[], failed_checks=[])
    with pytest.raises((AttributeError, TypeError)):
        result.passed = False  # type: ignore[misc]


def test_validator_hallucination_rule_contradiction():
    """Rule engine says water_now but answer forbids watering → hallucination."""
    ctx = _make_ctx(rule_primary_action="water_now")
    validator = AnswerValidator()
    answer = _valid_answer(행동="물주기 불필요합니다. 현재 수분이 충분합니다.")
    result = validator.validate(answer, ctx)
    assert result.passed is False
    assert "hallucination" in result.failed_checks


def test_validator_no_hallucination_when_rule_is_none():
    """rule_primary_action=none + anti-water phrase → no contradiction flagged."""
    ctx = _make_ctx(rule_primary_action="none")
    validator = AnswerValidator()
    # "물주기 불필요" without a watering rule → not a contradiction
    answer = _valid_answer(행동="물주기 불필요합니다. 현재 수분이 충분합니다.")
    result = validator.validate(answer, ctx)
    # hallucination check should not fire (rule doesn't say water_now)
    assert "hallucination" not in result.failed_checks


def test_validator_hallucination_chunk_claim_without_data():
    """Answer claims chunk knowledge when there are no retrieved chunks."""
    ctx = _make_ctx(retrieved_chunks=[])
    validator = AnswerValidator()
    answer = _valid_answer(근거="지식 청크에 따르면 몬스테라는 주 1회 물을 필요로 합니다.")
    result = validator.validate(answer, ctx)
    assert "hallucination" in result.failed_checks


# ---------------------------------------------------------------------------
# Correction prompt builder
# ---------------------------------------------------------------------------


def test_build_correction_prompt_contains_marker():
    result = ValidationResult(
        passed=False,
        errors=["[결론] 누락"],
        failed_checks=["format"],
    )
    prompt = _build_correction_prompt("original system prompt", result)
    assert "SELF_CORRECTION_REQUEST" in prompt


def test_build_correction_prompt_contains_errors():
    result = ValidationResult(
        passed=False,
        errors=["[결론] 누락", "[행동] 누락"],
        failed_checks=["format"],
    )
    prompt = _build_correction_prompt("original", result)
    assert "[결론] 누락" in prompt
    assert "[행동] 누락" in prompt


def test_build_correction_prompt_appends_original():
    result = ValidationResult(passed=False, errors=["err"], failed_checks=["format"])
    original = "ORIGINAL_SYSTEM_CONTENT"
    prompt = _build_correction_prompt(original, result)
    assert original in prompt


# ---------------------------------------------------------------------------
# MockHealingLLMClient
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mock_healing_returns_broken_on_error_trigger():
    client = MockHealingLLMClient()
    req = _make_request("error-trigger prompt")
    resp = await client.complete(req)
    assert "[결론]" not in resp.content
    assert resp.finish_reason == "error"


@pytest.mark.asyncio
async def test_mock_healing_returns_valid_on_correction():
    client = MockHealingLLMClient()
    req = _make_request("SELF_CORRECTION_REQUEST error-trigger prompt")
    resp = await client.complete(req)
    assert "[결론]" in resp.content


@pytest.mark.asyncio
async def test_mock_healing_normal_prompt_always_valid():
    client = MockHealingLLMClient()
    req = _make_request("normal system prompt without trigger")
    resp = await client.complete(req)
    assert "[결론]" in resp.content


@pytest.mark.asyncio
async def test_mock_healing_call_count_increments():
    client = MockHealingLLMClient()
    req = _make_request("normal prompt")
    await client.complete(req)
    await client.complete(req)
    assert client.call_count == 2


# ---------------------------------------------------------------------------
# SelfHealingOrchestrator: happy path (no healing needed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_healer_passes_on_first_attempt():
    from app.llm.mock_client import MockLLMClient

    ctx = _make_ctx()
    req = _make_request("normal prompt with no trigger")
    healer = SelfHealingOrchestrator()
    result = await healer.run_with_healing(
        llm_client=MockLLMClient(), llm_request=req, ctx=ctx
    )
    assert result.total_attempts == 1
    assert result.healing_occurred is False
    assert result.attempts[0].validation_result.passed is True
    assert result.parsed_answer.결론 != ""


# ---------------------------------------------------------------------------
# SelfHealingOrchestrator: healing path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_healer_triggers_retry_on_error_trigger():
    ctx = _make_ctx()
    req = _make_request("error-trigger: intentional failure")
    healer = SelfHealingOrchestrator()
    client = MockHealingLLMClient()
    result = await healer.run_with_healing(
        llm_client=client, llm_request=req, ctx=ctx
    )
    # Attempt 1 fails (error-trigger), attempt 2 succeeds (correction prompt)
    assert result.total_attempts >= 2
    assert result.healing_occurred is True
    assert result.attempts[0].validation_result.passed is False
    assert result.attempts[-1].validation_result.passed is True


@pytest.mark.asyncio
async def test_healer_correction_prompt_stored_on_first_failure():
    ctx = _make_ctx()
    req = _make_request("error-trigger prompt")
    healer = SelfHealingOrchestrator()
    result = await healer.run_with_healing(
        llm_client=MockHealingLLMClient(), llm_request=req, ctx=ctx
    )
    # First attempt should have a correction_prompt stored (used for attempt 2)
    assert result.attempts[0].correction_prompt is not None
    assert "SELF_CORRECTION_REQUEST" in result.attempts[0].correction_prompt


@pytest.mark.asyncio
async def test_healer_final_attempt_has_no_correction_prompt():
    ctx = _make_ctx()
    req = _make_request("error-trigger prompt")
    healer = SelfHealingOrchestrator()
    result = await healer.run_with_healing(
        llm_client=MockHealingLLMClient(), llm_request=req, ctx=ctx
    )
    # Last attempt never has a correction_prompt (no next attempt follows it)
    assert result.attempts[-1].correction_prompt is None


# ---------------------------------------------------------------------------
# SelfHealingOrchestrator: max attempts cap
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_healer_caps_at_max_attempts():
    """An always-failing mock must stop at MAX_ATTEMPTS."""

    class AlwaysFailingClient:
        async def complete(self, req: LLMRequest):
            from app.llm.mock_healing_client import _META
            from app.services.llm_port import LLMResponse

            return LLMResponse(
                request_id=req.request_id,
                content="",  # empty → format fails
                prompt_hash=req.prompt_hash,
                model_metadata=_META,
                input_tokens=1,
                output_tokens=0,
                finish_reason="error",
            )

    ctx = _make_ctx()
    req = _make_request("always failing prompt")
    healer = SelfHealingOrchestrator()
    result = await healer.run_with_healing(
        llm_client=AlwaysFailingClient(), llm_request=req, ctx=ctx
    )
    assert result.total_attempts == MAX_ATTEMPTS
    assert result.attempts[-1].validation_result.passed is False
    assert result.healing_occurred is True


# ---------------------------------------------------------------------------
# SelfHealingOrchestrator: final response is always returned (even on failure)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_healer_returns_final_response_even_on_all_failures():
    class AlwaysFailingClient:
        async def complete(self, req: LLMRequest):
            from app.llm.mock_healing_client import _META
            from app.services.llm_port import LLMResponse

            return LLMResponse(
                request_id=req.request_id,
                content="",
                prompt_hash=req.prompt_hash,
                model_metadata=_META,
                input_tokens=1,
                output_tokens=0,
                finish_reason="error",
            )

    ctx = _make_ctx()
    req = _make_request("always failing")
    result = await SelfHealingOrchestrator().run_with_healing(
        llm_client=AlwaysFailingClient(), llm_request=req, ctx=ctx
    )
    assert result.final_llm_response is not None
    assert result.parsed_answer is not None


# ---------------------------------------------------------------------------
# Audit schema: HealingAttemptSummary and ChatRunEvidenceView
# ---------------------------------------------------------------------------


def test_audit_view_has_healing_attempts_field():
    from app.schemas.audit_view import ChatRunEvidenceView

    fields = ChatRunEvidenceView.model_fields
    assert "healing_attempts" in fields
    assert fields["healing_attempts"].default == []


def test_healing_attempt_summary_fields():
    from app.schemas.audit_view import HealingAttemptSummary

    summary = HealingAttemptSummary(
        attempt_number=1,
        passed=False,
        failed_checks=["format"],
        validation_errors=["[결론] 누락"],
    )
    assert summary.attempt_number == 1
    assert summary.passed is False
    assert "format" in summary.failed_checks


# ---------------------------------------------------------------------------
# DB model: LlmSelfHealingLog
# ---------------------------------------------------------------------------


def test_llm_self_healing_log_table_columns():
    from app.models.llm_self_healing_log import LlmSelfHealingLog

    cols = LlmSelfHealingLog.__table__.columns
    assert "id" in cols
    assert "request_id" in cols
    assert "attempt_number" in cols
    assert "passed" in cols
    assert "failed_checks" in cols
    assert "validation_errors" in cols
    assert "correction_prompt_snippet" in cols
    assert "response_snippet" in cols
    assert "created_at" in cols


# ---------------------------------------------------------------------------
# MAX_ATTEMPTS constant is accessible and positive
# ---------------------------------------------------------------------------


def test_max_attempts_is_positive():
    assert MAX_ATTEMPTS >= 1
