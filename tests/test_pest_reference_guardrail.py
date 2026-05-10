"""TICKET-019 — PestReferenceGuardrail + NonDiagnosticAnswerValidator tests."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.chat_answer import ParsedAnswer
from app.services.pest_reference_guardrail import (
    DIAGNOSTIC_PATTERNS,
    REQUIRED_DISCLAIMER,
    NonDiagnosticAnswerValidator,
    PestGuardrailResult,
    PestReferenceGuardrail,
    ValidationResult,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _parsed(
    결론: str = "증상이 관찰됩니다",
    근거: str = "지식 청크 기반",
    행동: str = "전문가에게 문의하세요",
    주의: str = "주의가 필요합니다",
) -> ParsedAnswer:
    return ParsedAnswer(결론=결론, 근거=근거, 행동=행동, 주의=주의)


def _with_disclaimer(**kwargs) -> ParsedAnswer:
    base = _parsed(**kwargs)
    return ParsedAnswer(
        결론=base.결론,
        근거=base.근거,
        행동=base.행동,
        주의=f"{base.주의} {REQUIRED_DISCLAIMER}.",
    )


# ---------------------------------------------------------------------------
# NonDiagnosticAnswerValidator — clean answer
# ---------------------------------------------------------------------------


def test_validator_clean_answer_passes() -> None:
    parsed = _with_disclaimer()
    result = NonDiagnosticAnswerValidator().validate(parsed)
    assert isinstance(result, ValidationResult)
    assert result.is_valid is True
    assert result.flagged_phrases == ()
    assert result.has_disclaimer is True


def test_validator_no_flagged_phrases_on_clean_text() -> None:
    parsed = _with_disclaimer(결론="증상이 보이면 관찰하세요", 행동="기다리세요")
    result = NonDiagnosticAnswerValidator().validate(parsed)
    assert len(result.flagged_phrases) == 0


# ---------------------------------------------------------------------------
# NonDiagnosticAnswerValidator — diagnostic language detection
# ---------------------------------------------------------------------------


def test_validator_flags_병입니다() -> None:
    parsed = _parsed(결론="이것은 탄저병입니다")
    result = NonDiagnosticAnswerValidator().validate(parsed)
    assert "병입니다" in result.flagged_phrases
    assert result.is_valid is False


def test_validator_flags_균입니다() -> None:
    parsed = _parsed(근거="흰가루균입니다")
    result = NonDiagnosticAnswerValidator().validate(parsed)
    assert "균입니다" in result.flagged_phrases


def test_validator_flags_해충입니다() -> None:
    parsed = _parsed(결론="이것은 진딧물해충입니다")
    result = NonDiagnosticAnswerValidator().validate(parsed)
    assert "해충입니다" in result.flagged_phrases


def test_validator_flags_확진() -> None:
    parsed = _parsed(결론="확진된 흰가루병입니다")
    result = NonDiagnosticAnswerValidator().validate(parsed)
    assert "확진" in result.flagged_phrases


def test_validator_flags_처방() -> None:
    parsed = _parsed(행동="전문가 처방에 따라 조치하세요")
    result = NonDiagnosticAnswerValidator().validate(parsed)
    assert "처방" in result.flagged_phrases


def test_validator_flags_살균제_command() -> None:
    parsed = _parsed(행동="살균제를 사용하세요")
    result = NonDiagnosticAnswerValidator().validate(parsed)
    assert "살균제를 사용" in result.flagged_phrases


def test_validator_flags_살충제_command() -> None:
    parsed = _parsed(행동="살충제를 사용하여 제거하세요")
    result = NonDiagnosticAnswerValidator().validate(parsed)
    assert "살충제를 사용" in result.flagged_phrases


def test_validator_flags_농약_command() -> None:
    parsed = _parsed(행동="농약을 사용하세요")
    result = NonDiagnosticAnswerValidator().validate(parsed)
    assert "농약을 사용" in result.flagged_phrases


def test_validator_multiple_flags_collected() -> None:
    parsed = _parsed(결론="탄저병입니다", 행동="살균제를 사용하세요")
    result = NonDiagnosticAnswerValidator().validate(parsed)
    assert "병입니다" in result.flagged_phrases
    assert "살균제를 사용" in result.flagged_phrases
    assert len(result.flagged_phrases) >= 2


# ---------------------------------------------------------------------------
# NonDiagnosticAnswerValidator — disclaimer detection
# ---------------------------------------------------------------------------


def test_validator_missing_disclaimer_fails() -> None:
    parsed = _parsed(주의="조심하세요")
    result = NonDiagnosticAnswerValidator().validate(parsed)
    assert result.has_disclaimer is False
    assert result.is_valid is False


def test_validator_disclaimer_in_주의_detected() -> None:
    parsed = _parsed(주의=f"추가 주의. {REQUIRED_DISCLAIMER}.")
    result = NonDiagnosticAnswerValidator().validate(parsed)
    assert result.has_disclaimer is True


def test_validator_disclaimer_only_checked_in_주의() -> None:
    parsed = ParsedAnswer(
        결론=f"{REQUIRED_DISCLAIMER}",  # disclaimer in wrong section
        근거="",
        행동="",
        주의="주의 사항",  # not in 주의
    )
    result = NonDiagnosticAnswerValidator().validate(parsed)
    assert result.has_disclaimer is False


# ---------------------------------------------------------------------------
# PestReferenceGuardrail — safety metadata flags
# ---------------------------------------------------------------------------


def test_guardrail_sets_is_reference_only_true() -> None:
    result = PestReferenceGuardrail().apply(_parsed())
    assert result.is_reference_only is True


def test_guardrail_sets_diagnosis_allowed_false() -> None:
    result = PestReferenceGuardrail().apply(_parsed())
    assert result.diagnosis_allowed is False


def test_guardrail_returns_pest_guardrail_result_type() -> None:
    result = PestReferenceGuardrail().apply(_parsed())
    assert isinstance(result, PestGuardrailResult)


def test_guardrail_includes_validation_result() -> None:
    result = PestReferenceGuardrail().apply(_parsed())
    assert isinstance(result.validation, ValidationResult)


# ---------------------------------------------------------------------------
# PestReferenceGuardrail — disclaimer injection
# ---------------------------------------------------------------------------


def test_guardrail_injects_disclaimer_when_missing() -> None:
    parsed = _parsed(주의="일반 주의 사항")
    result = PestReferenceGuardrail().apply(parsed)
    assert REQUIRED_DISCLAIMER in result.answer.주의


def test_guardrail_does_not_duplicate_disclaimer() -> None:
    parsed = _with_disclaimer()
    result = PestReferenceGuardrail().apply(parsed)
    assert result.answer.주의.count(REQUIRED_DISCLAIMER) == 1


def test_guardrail_disclaimer_injection_makes_validation_pass() -> None:
    parsed = _parsed(주의="주의")  # no disclaimer, no diagnostic
    result = PestReferenceGuardrail().apply(parsed)
    assert result.validation.has_disclaimer is True


def test_guardrail_preserves_결론_section() -> None:
    parsed = _parsed(결론="특정 결론 내용")
    result = PestReferenceGuardrail().apply(parsed)
    assert result.answer.결론 == "특정 결론 내용"


def test_guardrail_preserves_근거_section() -> None:
    parsed = _parsed(근거="근거 내용")
    result = PestReferenceGuardrail().apply(parsed)
    assert result.answer.근거 == "근거 내용"


def test_guardrail_preserves_행동_section() -> None:
    parsed = _parsed(행동="행동 내용")
    result = PestReferenceGuardrail().apply(parsed)
    assert result.answer.행동 == "행동 내용"


def test_guardrail_주의_extended_not_replaced() -> None:
    original_주의 = "과습 주의"
    parsed = _parsed(주의=original_주의)
    result = PestReferenceGuardrail().apply(parsed)
    assert original_주의 in result.answer.주의
    assert REQUIRED_DISCLAIMER in result.answer.주의


def test_guardrail_empty_주의_gets_disclaimer() -> None:
    parsed = _parsed(주의="")
    result = PestReferenceGuardrail().apply(parsed)
    assert REQUIRED_DISCLAIMER in result.answer.주의


# ---------------------------------------------------------------------------
# DIAGNOSTIC_PATTERNS constant sanity
# ---------------------------------------------------------------------------


def test_diagnostic_patterns_is_tuple() -> None:
    assert isinstance(DIAGNOSTIC_PATTERNS, tuple)
    assert len(DIAGNOSTIC_PATTERNS) > 0


def test_required_disclaimer_is_nonempty_string() -> None:
    assert isinstance(REQUIRED_DISCLAIMER, str)
    assert len(REQUIRED_DISCLAIMER) > 10


# ---------------------------------------------------------------------------
# Orchestrator integration — pest intent triggers guardrail
# ---------------------------------------------------------------------------


def _make_session() -> MagicMock:
    session = MagicMock()
    session.get = AsyncMock(return_value=None)
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


def _make_forward_context(plant_id, user_id, question):
    from app.domain.evidence import ForwardContext

    ctx = MagicMock(spec=ForwardContext)
    ctx.plant_id = plant_id
    ctx.user_id = user_id
    ctx.question = question
    ctx.intent = "pest_reference_question"
    ctx.rule_evidence_facts = {}
    ctx.rule_reason_codes = []
    ctx.rule_primary_action = "none"
    ctx.source_coverage = {"pest_disease_reference": True, "species_profile": False}
    ctx.retrieved_chunks = []
    ctx.rag_layers = ["pest_disease_reference", "species_profile"]
    ctx.recent_care_logs = []
    ctx.character = None
    ctx.snapshot = None
    ctx.evidence_hash = "deadbeef"
    return ctx


@pytest.mark.asyncio
async def test_orchestrator_pest_sets_reference_only_flag() -> None:
    from app.services.chat_orchestrator import ChatOrchestrator
    from app.services.llm_port import LLMResponse, ModelMetadata

    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    request_id = uuid.uuid4()
    question = "병충해 어떻게 해?"

    orchestrator = ChatOrchestrator()
    session = _make_session()

    plant_mock = MagicMock()
    plant_mock.species_profile_id = None
    session.get = AsyncMock(side_effect=[None, plant_mock])

    ctx = _make_forward_context(plant_id, user_id, question)
    pest_content = (
        "[결론] 증상이 관찰됩니다.\n\n"
        "[근거] 지식 청크 기반.\n\n"
        "[행동] 전문가에게 문의하세요.\n\n"
        "[주의] ※ 병충해 정보는 참고용 지식으로만 활용하세요."
    )
    llm_resp = LLMResponse(
        request_id=request_id,
        content=pest_content,
        prompt_hash="abc",
        model_metadata=ModelMetadata(model_name="mock-model-v1", provider="mock"),
        input_tokens=10,
        output_tokens=20,
        finish_reason="stop",
    )

    with (
        patch("app.services.chat_orchestrator._CLASSIFIER") as mock_cls,
        patch("app.services.chat_orchestrator.RetrievalService") as mock_ret_cls,
        patch("app.services.chat_orchestrator.EvidenceBuilderService") as mock_ev_cls,
        patch("app.services.chat_orchestrator._PROMPT_BUILDER") as mock_pb,
        patch("app.services.chat_orchestrator._LLM_CLIENT") as mock_llm,
    ):
        mock_cls.classify.return_value = ("pest_reference_question", 0.9, "rule")
        mock_ret_cls.return_value.query = AsyncMock(
            return_value=MagicMock(request_id=uuid.uuid4())
        )
        mock_ev_cls.return_value.build = AsyncMock(return_value=(ctx, False))

        from app.domain.prompt_build_result import PromptBuildResult

        pr = MagicMock(spec=PromptBuildResult)
        pr.system_prompt = "식물 관리 AI"
        pr.user_turn = question
        pr.prompt_hash = "abc"
        pr.guardrails_applied = ("pest_reference_only",)
        mock_pb.build.return_value = pr
        mock_llm.complete = AsyncMock(return_value=llm_resp)

        resp = await orchestrator.run(
            session,
            plant_id=plant_id,
            user_id=user_id,
            question=question,
            request_id=request_id,
        )

    assert resp.is_reference_only is True
    assert resp.diagnosis_allowed is False


@pytest.mark.asyncio
async def test_orchestrator_pest_주의_contains_disclaimer() -> None:
    from app.services.chat_orchestrator import ChatOrchestrator
    from app.services.llm_port import LLMResponse, ModelMetadata

    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    request_id = uuid.uuid4()
    question = "병충해"

    orchestrator = ChatOrchestrator()
    session = _make_session()

    plant_mock = MagicMock()
    plant_mock.species_profile_id = None
    session.get = AsyncMock(side_effect=[None, plant_mock])

    ctx = _make_forward_context(plant_id, user_id, question)
    # Deliberately omit the REQUIRED_DISCLAIMER — guardrail must inject it
    pest_content = (
        "[결론] 증상 관찰.\n\n"
        "[근거] 지식 기반.\n\n"
        "[행동] 문의.\n\n"
        "[주의] 주의 필요."
    )
    llm_resp = LLMResponse(
        request_id=request_id,
        content=pest_content,
        prompt_hash="abc",
        model_metadata=ModelMetadata(model_name="mock-model-v1", provider="mock"),
        input_tokens=5,
        output_tokens=10,
        finish_reason="stop",
    )

    with (
        patch("app.services.chat_orchestrator._CLASSIFIER") as mock_cls,
        patch("app.services.chat_orchestrator.RetrievalService") as mock_ret_cls,
        patch("app.services.chat_orchestrator.EvidenceBuilderService") as mock_ev_cls,
        patch("app.services.chat_orchestrator._PROMPT_BUILDER") as mock_pb,
        patch("app.services.chat_orchestrator._LLM_CLIENT") as mock_llm,
    ):
        mock_cls.classify.return_value = ("pest_reference_question", 0.9, "rule")
        mock_ret_cls.return_value.query = AsyncMock(
            return_value=MagicMock(request_id=uuid.uuid4())
        )
        mock_ev_cls.return_value.build = AsyncMock(return_value=(ctx, False))

        from app.domain.prompt_build_result import PromptBuildResult

        pr = MagicMock(spec=PromptBuildResult)
        pr.system_prompt = "s"
        pr.user_turn = question
        pr.prompt_hash = "abc"
        pr.guardrails_applied = ("pest_reference_only",)
        mock_pb.build.return_value = pr
        mock_llm.complete = AsyncMock(return_value=llm_resp)

        resp = await orchestrator.run(
            session,
            plant_id=plant_id,
            user_id=user_id,
            question=question,
            request_id=request_id,
        )

    assert REQUIRED_DISCLAIMER in resp.answer.주의


@pytest.mark.asyncio
async def test_orchestrator_non_pest_flags_are_false_and_true() -> None:
    from app.services.chat_orchestrator import ChatOrchestrator
    from app.services.llm_port import LLMResponse, ModelMetadata

    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    request_id = uuid.uuid4()
    question = "물주기 언제?"

    orchestrator = ChatOrchestrator()
    session = _make_session()

    plant_mock = MagicMock()
    plant_mock.species_profile_id = None
    session.get = AsyncMock(side_effect=[None, plant_mock])

    from app.domain.evidence import ForwardContext

    ctx = MagicMock(spec=ForwardContext)
    ctx.plant_id = plant_id
    ctx.user_id = user_id
    ctx.question = question
    ctx.intent = "watering_question"
    ctx.rule_evidence_facts = {}
    ctx.rule_reason_codes = []
    ctx.rule_primary_action = "none"
    ctx.source_coverage = {}
    ctx.retrieved_chunks = []
    ctx.rag_layers = ["care_knowledge", "species_profile"]
    ctx.recent_care_logs = []
    ctx.character = None
    ctx.snapshot = None
    ctx.evidence_hash = "abc"

    llm_resp = LLMResponse(
        request_id=request_id,
        content="[결론] A\n\n[근거] B\n\n[행동] C\n\n[주의] D",
        prompt_hash="abc",
        model_metadata=ModelMetadata(model_name="mock-model-v1", provider="mock"),
        input_tokens=5,
        output_tokens=10,
        finish_reason="stop",
    )

    with (
        patch("app.services.chat_orchestrator._CLASSIFIER") as mock_cls,
        patch("app.services.chat_orchestrator.RetrievalService") as mock_ret_cls,
        patch("app.services.chat_orchestrator.EvidenceBuilderService") as mock_ev_cls,
        patch("app.services.chat_orchestrator._PROMPT_BUILDER") as mock_pb,
        patch("app.services.chat_orchestrator._LLM_CLIENT") as mock_llm,
    ):
        mock_cls.classify.return_value = ("watering_question", 0.9, "rule")
        mock_ret_cls.return_value.query = AsyncMock(
            return_value=MagicMock(request_id=uuid.uuid4())
        )
        mock_ev_cls.return_value.build = AsyncMock(return_value=(ctx, False))

        from app.domain.prompt_build_result import PromptBuildResult

        pr = MagicMock(spec=PromptBuildResult)
        pr.system_prompt = "s"
        pr.user_turn = question
        pr.prompt_hash = "abc"
        pr.guardrails_applied = ()
        mock_pb.build.return_value = pr
        mock_llm.complete = AsyncMock(return_value=llm_resp)

        resp = await orchestrator.run(
            session,
            plant_id=plant_id,
            user_id=user_id,
            question=question,
            request_id=request_id,
        )

    assert resp.is_reference_only is False
    assert resp.diagnosis_allowed is True
