"""TICKET-018 — ChatOrchestrator + ResponseParser tests (no network, no DB)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.chat_answer import ChatAnswerResponse, ParsedAnswer
from app.services.chat_orchestrator import ChatOrchestrator
from app.services.response_parser import parse_answer


# ---------------------------------------------------------------------------
# ResponseParser
# ---------------------------------------------------------------------------


def test_parse_answer_all_sections() -> None:
    content = "[결론] A\n\n[근거] B\n\n[행동] C\n\n[주의] D"
    r = parse_answer(content)
    assert r.결론 == "A"
    assert r.근거 == "B"
    assert r.행동 == "C"
    assert r.주의 == "D"


def test_parse_answer_multiline_content() -> None:
    content = "[결론] line1\nline2\n\n[근거] basis\n\n[행동] action\n\n[주의] caution"
    r = parse_answer(content)
    assert "line1" in r.결론
    assert "line2" in r.결론
    assert r.근거 == "basis"


def test_parse_answer_missing_section_returns_empty() -> None:
    content = "[결론] only conclusion"
    r = parse_answer(content)
    assert r.결론 == "only conclusion"
    assert r.근거 == ""
    assert r.행동 == ""
    assert r.주의 == ""


def test_parse_answer_empty_content() -> None:
    r = parse_answer("")
    assert r.결론 == ""
    assert r.근거 == ""
    assert r.행동 == ""
    assert r.주의 == ""


def test_parse_answer_with_real_mock_response() -> None:
    content = (
        "[결론] 현재 식물 상태를 분석했습니다.\n\n"
        "[근거] 룰 엔진 분석 결과를 적용했습니다.\n\n"
        "[행동] 오늘 토양 수분을 확인하세요.\n\n"
        "[주의] 과도한 관리는 해가 됩니다."
    )
    r = parse_answer(content)
    assert "식물 상태" in r.결론
    assert "룰 엔진" in r.근거
    assert "토양 수분" in r.행동
    assert "과도한" in r.주의


def test_parse_answer_is_parsed_answer_instance() -> None:
    r = parse_answer("[결론] x\n\n[근거] y\n\n[행동] z\n\n[주의] w")
    assert isinstance(r, ParsedAnswer)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_session() -> MagicMock:
    session = MagicMock()
    session.get = AsyncMock(return_value=None)
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


def _make_forward_context(
    plant_id: uuid.UUID, user_id: uuid.UUID, question: str
) -> MagicMock:
    from app.domain.evidence import ForwardContext

    ctx = MagicMock(spec=ForwardContext)
    ctx.plant_id = plant_id
    ctx.user_id = user_id
    ctx.question = question
    ctx.intent = "watering_question"
    ctx.rule_evidence_facts = {}
    ctx.rule_reason_codes = []
    ctx.rule_primary_action = "none"
    ctx.source_coverage = {"care_knowledge": True, "species_profile": False}
    ctx.retrieved_chunks = []
    ctx.rag_layers = ["care_knowledge", "species_profile"]
    ctx.recent_care_logs = []
    ctx.character = None
    ctx.snapshot = None
    ctx.evidence_hash = "deadbeef"
    return ctx


def _make_llm_response(request_id: uuid.UUID, content: str):
    from app.services.llm_port import LLMResponse, ModelMetadata

    return LLMResponse(
        request_id=request_id,
        content=content,
        prompt_hash="abc123",
        model_metadata=ModelMetadata(model_name="mock-model-v1", provider="mock"),
        input_tokens=10,
        output_tokens=20,
        finish_reason="stop",
    )


_SAMPLE_CONTENT = (
    "[결론] 물주기 필요\n\n"
    "[근거] 토양 수분 부족\n\n"
    "[행동] 지금 물을 주세요\n\n"
    "[주의] 과습 주의"
)


# ---------------------------------------------------------------------------
# ChatOrchestrator.run — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_returns_chat_answer_response() -> None:
    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    request_id = uuid.uuid4()
    question = "물주기 알려줘"

    orchestrator = ChatOrchestrator()
    session = _make_session()

    plant_mock = MagicMock()
    plant_mock.species_profile_id = uuid.uuid4()
    # First get: ChatRequest (None = new) / Second get: Plant
    session.get = AsyncMock(side_effect=[None, plant_mock])

    ctx = _make_forward_context(plant_id, user_id, question)
    llm_resp = _make_llm_response(request_id, _SAMPLE_CONTENT)

    with (
        patch("app.services.chat_orchestrator._CLASSIFIER") as mock_cls,
        patch("app.services.chat_orchestrator.RetrievalService") as mock_ret_cls,
        patch("app.services.chat_orchestrator.EvidenceBuilderService") as mock_ev_cls,
        patch("app.services.chat_orchestrator._PROMPT_BUILDER") as mock_pb,
        patch("app.services.chat_orchestrator._LLM_CLIENT") as mock_llm,
    ):
        mock_cls.classify.return_value = ("watering_question", 0.95, "rule")

        ret_instance = MagicMock()
        ret_instance.query = AsyncMock(return_value=MagicMock(request_id=uuid.uuid4()))
        mock_ret_cls.return_value = ret_instance

        ev_instance = MagicMock()
        ev_instance.build = AsyncMock(return_value=(ctx, False))
        mock_ev_cls.return_value = ev_instance

        from app.domain.prompt_build_result import PromptBuildResult

        pr = MagicMock(spec=PromptBuildResult)
        pr.system_prompt = "식물 관리 AI"
        pr.user_turn = question
        pr.prompt_hash = "abc123"
        pr.guardrails_applied = ("rule_engine_authority",)
        mock_pb.build.return_value = pr

        mock_llm.complete = AsyncMock(return_value=llm_resp)

        resp = await orchestrator.run(
            session,
            plant_id=plant_id,
            user_id=user_id,
            question=question,
            request_id=request_id,
        )

    assert isinstance(resp, ChatAnswerResponse)
    assert resp.request_id == request_id
    assert resp.plant_id == plant_id
    assert resp.intent == "watering_question"
    assert resp.from_cache is False


@pytest.mark.asyncio
async def test_orchestrator_parsed_sections() -> None:
    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    request_id = uuid.uuid4()
    question = "물주기"

    orchestrator = ChatOrchestrator()
    session = _make_session()

    plant_mock = MagicMock()
    plant_mock.species_profile_id = None
    session.get = AsyncMock(side_effect=[None, plant_mock])

    ctx = _make_forward_context(plant_id, user_id, question)
    llm_resp = _make_llm_response(request_id, _SAMPLE_CONTENT)

    with (
        patch("app.services.chat_orchestrator._CLASSIFIER") as mock_cls,
        patch("app.services.chat_orchestrator.RetrievalService") as mock_ret_cls,
        patch("app.services.chat_orchestrator.EvidenceBuilderService") as mock_ev_cls,
        patch("app.services.chat_orchestrator._PROMPT_BUILDER") as mock_pb,
        patch("app.services.chat_orchestrator._LLM_CLIENT") as mock_llm,
    ):
        mock_cls.classify.return_value = ("watering_question", 0.95, "rule")
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

    assert resp.answer.결론 == "물주기 필요"
    assert resp.answer.근거 == "토양 수분 부족"
    assert resp.answer.행동 == "지금 물을 주세요"
    assert resp.answer.주의 == "과습 주의"


@pytest.mark.asyncio
async def test_orchestrator_persists_chat_request_and_llm_run() -> None:
    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    request_id = uuid.uuid4()
    question = "물주기"

    orchestrator = ChatOrchestrator()
    session = _make_session()

    plant_mock = MagicMock()
    plant_mock.species_profile_id = None
    session.get = AsyncMock(side_effect=[None, plant_mock])

    ctx = _make_forward_context(plant_id, user_id, question)
    llm_resp = _make_llm_response(request_id, _SAMPLE_CONTENT)

    with (
        patch("app.services.chat_orchestrator._CLASSIFIER") as mock_cls,
        patch("app.services.chat_orchestrator.RetrievalService") as mock_ret_cls,
        patch("app.services.chat_orchestrator.EvidenceBuilderService") as mock_ev_cls,
        patch("app.services.chat_orchestrator._PROMPT_BUILDER") as mock_pb,
        patch("app.services.chat_orchestrator._LLM_CLIENT") as mock_llm,
    ):
        mock_cls.classify.return_value = ("watering_question", 0.95, "rule")
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

        await orchestrator.run(
            session,
            plant_id=plant_id,
            user_id=user_id,
            question=question,
            request_id=request_id,
        )

    from app.models.chat_request import ChatRequest
    from app.models.llm_run import LlmRun

    assert session.add.call_count == 2
    added_types = [type(call.args[0]) for call in session.add.call_args_list]
    assert ChatRequest in added_types
    assert LlmRun in added_types


@pytest.mark.asyncio
async def test_orchestrator_llm_run_profile_is_chat_orchestrator() -> None:
    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    request_id = uuid.uuid4()
    question = "물주기"

    orchestrator = ChatOrchestrator()
    session = _make_session()

    plant_mock = MagicMock()
    plant_mock.species_profile_id = None
    session.get = AsyncMock(side_effect=[None, plant_mock])

    ctx = _make_forward_context(plant_id, user_id, question)
    llm_resp = _make_llm_response(request_id, _SAMPLE_CONTENT)

    with (
        patch("app.services.chat_orchestrator._CLASSIFIER") as mock_cls,
        patch("app.services.chat_orchestrator.RetrievalService") as mock_ret_cls,
        patch("app.services.chat_orchestrator.EvidenceBuilderService") as mock_ev_cls,
        patch("app.services.chat_orchestrator._PROMPT_BUILDER") as mock_pb,
        patch("app.services.chat_orchestrator._LLM_CLIENT") as mock_llm,
    ):
        mock_cls.classify.return_value = ("watering_question", 0.95, "rule")
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

        await orchestrator.run(
            session,
            plant_id=plant_id,
            user_id=user_id,
            question=question,
            request_id=request_id,
        )

    from app.models.llm_run import LlmRun

    llm_run_calls = [
        call.args[0]
        for call in session.add.call_args_list
        if isinstance(call.args[0], LlmRun)
    ]
    assert len(llm_run_calls) == 1
    assert llm_run_calls[0].profile == "chat_orchestrator"


@pytest.mark.asyncio
async def test_orchestrator_tokens_echoed_in_response() -> None:
    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    request_id = uuid.uuid4()
    question = "q"

    orchestrator = ChatOrchestrator()
    session = _make_session()

    plant_mock = MagicMock()
    plant_mock.species_profile_id = None
    session.get = AsyncMock(side_effect=[None, plant_mock])

    ctx = _make_forward_context(plant_id, user_id, question)
    llm_resp = _make_llm_response(request_id, _SAMPLE_CONTENT)

    with (
        patch("app.services.chat_orchestrator._CLASSIFIER") as mock_cls,
        patch("app.services.chat_orchestrator.RetrievalService") as mock_ret_cls,
        patch("app.services.chat_orchestrator.EvidenceBuilderService") as mock_ev_cls,
        patch("app.services.chat_orchestrator._PROMPT_BUILDER") as mock_pb,
        patch("app.services.chat_orchestrator._LLM_CLIENT") as mock_llm,
    ):
        mock_cls.classify.return_value = ("watering_question", 0.95, "rule")
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

    assert resp.input_tokens == 10
    assert resp.output_tokens == 20
    assert resp.model_name == "mock-model-v1"
    assert resp.prompt_hash == "abc123"


# ---------------------------------------------------------------------------
# companion_plant_question — no retrieval
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_companion_skips_retrieval() -> None:
    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    request_id = uuid.uuid4()
    question = "같이 키울 식물 추천해줘"

    orchestrator = ChatOrchestrator()
    session = _make_session()
    # companion_plant_question has empty rag_layers → no Plant lookup for retrieval
    session.get = AsyncMock(return_value=None)  # only ChatRequest idempotency check

    ctx = _make_forward_context(plant_id, user_id, question)
    ctx.intent = "companion_plant_question"
    ctx.source_coverage = {}
    llm_resp = _make_llm_response(request_id, _SAMPLE_CONTENT)

    with (
        patch("app.services.chat_orchestrator._CLASSIFIER") as mock_cls,
        patch("app.services.chat_orchestrator.RetrievalService") as mock_ret_cls,
        patch("app.services.chat_orchestrator.EvidenceBuilderService") as mock_ev_cls,
        patch("app.services.chat_orchestrator._PROMPT_BUILDER") as mock_pb,
        patch("app.services.chat_orchestrator._LLM_CLIENT") as mock_llm,
    ):
        mock_cls.classify.return_value = ("companion_plant_question", 0.8, "rule")
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

    # Retrieval service was never instantiated (no rag_layers)
    mock_ret_cls.assert_not_called()
    assert isinstance(resp, ChatAnswerResponse)


# ---------------------------------------------------------------------------
# Retrieval failure is graceful
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_retrieval_failure_continues() -> None:
    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    request_id = uuid.uuid4()
    question = "빛은 얼마나 필요해?"

    orchestrator = ChatOrchestrator()
    session = _make_session()

    plant_mock = MagicMock()
    plant_mock.species_profile_id = None
    session.get = AsyncMock(side_effect=[None, plant_mock])

    ctx = _make_forward_context(plant_id, user_id, question)
    ctx.intent = "light_question"
    llm_resp = _make_llm_response(request_id, _SAMPLE_CONTENT)

    with (
        patch("app.services.chat_orchestrator._CLASSIFIER") as mock_cls,
        patch("app.services.chat_orchestrator.RetrievalService") as mock_ret_cls,
        patch("app.services.chat_orchestrator.EvidenceBuilderService") as mock_ev_cls,
        patch("app.services.chat_orchestrator._PROMPT_BUILDER") as mock_pb,
        patch("app.services.chat_orchestrator._LLM_CLIENT") as mock_llm,
    ):
        mock_cls.classify.return_value = ("light_question", 0.9, "rule")

        # Retrieval raises exception
        mock_ret_cls.return_value.query = AsyncMock(
            side_effect=RuntimeError("retrieval failed")
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

        # Must NOT raise despite retrieval failure
        resp = await orchestrator.run(
            session,
            plant_id=plant_id,
            user_id=user_id,
            question=question,
            request_id=request_id,
        )

    assert isinstance(resp, ChatAnswerResponse)
    assert resp.intent == "light_question"


# ---------------------------------------------------------------------------
# PlantNotFoundError propagates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_plant_not_found_raises() -> None:
    from app.services.evidence_builder import PlantNotFoundError

    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    request_id = uuid.uuid4()

    orchestrator = ChatOrchestrator()
    session = _make_session()

    plant_mock = MagicMock()
    plant_mock.species_profile_id = None
    session.get = AsyncMock(side_effect=[None, plant_mock])

    with (
        patch("app.services.chat_orchestrator._CLASSIFIER") as mock_cls,
        patch("app.services.chat_orchestrator.RetrievalService") as mock_ret_cls,
        patch("app.services.chat_orchestrator.EvidenceBuilderService") as mock_ev_cls,
        patch("app.services.chat_orchestrator._PROMPT_BUILDER"),
        patch("app.services.chat_orchestrator._LLM_CLIENT"),
    ):
        mock_cls.classify.return_value = ("watering_question", 0.9, "rule")
        mock_ret_cls.return_value.query = AsyncMock(
            return_value=MagicMock(request_id=uuid.uuid4())
        )
        mock_ev_cls.return_value.build = AsyncMock(
            side_effect=PlantNotFoundError("plant not found")
        )

        with pytest.raises(PlantNotFoundError):
            await orchestrator.run(
                session,
                plant_id=plant_id,
                user_id=user_id,
                question="물주기",
                request_id=request_id,
            )


# ---------------------------------------------------------------------------
# Idempotency — cached path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_cached_path() -> None:
    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    request_id = uuid.uuid4()
    now = datetime.now(UTC)

    from app.models.chat_request import ChatRequest
    from app.models.llm_run import LlmRun

    existing_chat = MagicMock(spec=ChatRequest)
    existing_chat.id = request_id
    existing_chat.plant_id = plant_id
    existing_chat.status = "watering_question"
    existing_chat.created_at = now

    existing_llm_run = MagicMock(spec=LlmRun)
    existing_llm_run.response_text = _SAMPLE_CONTENT
    existing_llm_run.prompt_hash = "cached_hash"
    existing_llm_run.model_name = "mock-model-v1"
    existing_llm_run.tokens_in = 5
    existing_llm_run.tokens_out = 15

    orchestrator = ChatOrchestrator()
    session = _make_session()
    session.get = AsyncMock(return_value=existing_chat)  # found → cached path

    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = existing_llm_run
    session.execute = AsyncMock(return_value=mock_scalar)

    resp = await orchestrator.run(
        session,
        plant_id=plant_id,
        user_id=user_id,
        question="물주기",
        request_id=request_id,
    )

    assert resp.from_cache is True
    assert resp.request_id == request_id
    assert resp.intent == "watering_question"
    assert resp.answer.결론 == "물주기 필요"
    assert resp.input_tokens == 5
    assert resp.output_tokens == 15
    # No new rows persisted
    session.add.assert_not_called()


# ---------------------------------------------------------------------------
# Guardrails are included in response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_guardrails_in_response() -> None:
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
    ctx.intent = "pest_reference_question"
    llm_resp = _make_llm_response(request_id, _SAMPLE_CONTENT)

    with (
        patch("app.services.chat_orchestrator._CLASSIFIER") as mock_cls,
        patch("app.services.chat_orchestrator.RetrievalService") as mock_ret_cls,
        patch("app.services.chat_orchestrator.EvidenceBuilderService") as mock_ev_cls,
        patch("app.services.chat_orchestrator._PROMPT_BUILDER") as mock_pb,
        patch("app.services.chat_orchestrator._LLM_CLIENT") as mock_llm,
    ):
        mock_cls.classify.return_value = ("pest_reference_question", 0.85, "rule")
        mock_ret_cls.return_value.query = AsyncMock(
            return_value=MagicMock(request_id=uuid.uuid4())
        )
        mock_ev_cls.return_value.build = AsyncMock(return_value=(ctx, False))

        from app.domain.prompt_build_result import PromptBuildResult

        pr = MagicMock(spec=PromptBuildResult)
        pr.system_prompt = "s"
        pr.user_turn = question
        pr.prompt_hash = "abc"
        pr.guardrails_applied = ("pest_reference_only", "rule_engine_authority")
        mock_pb.build.return_value = pr
        mock_llm.complete = AsyncMock(return_value=llm_resp)

        resp = await orchestrator.run(
            session,
            plant_id=plant_id,
            user_id=user_id,
            question=question,
            request_id=request_id,
        )

    assert "pest_reference_only" in resp.guardrails_applied
    assert "rule_engine_authority" in resp.guardrails_applied


# ---------------------------------------------------------------------------
# Intent-to-RAG-layer mapping
# ---------------------------------------------------------------------------


def test_intent_rag_layer_mapping_coverage() -> None:
    from app.services.chat_orchestrator import _INTENT_TO_RAG_LAYERS
    from app.schemas.chat_intent import ROUTING_TABLE

    for intent in ROUTING_TABLE:
        assert intent in _INTENT_TO_RAG_LAYERS, (
            f"Intent '{intent}' missing from _INTENT_TO_RAG_LAYERS"
        )


def test_companion_intent_has_empty_rag_layers() -> None:
    from app.services.chat_orchestrator import _INTENT_TO_RAG_LAYERS

    assert _INTENT_TO_RAG_LAYERS["companion_plant_question"] == []


def test_pest_intent_includes_pest_layer() -> None:
    from app.services.chat_orchestrator import _INTENT_TO_RAG_LAYERS

    assert "pest_disease_reference" in _INTENT_TO_RAG_LAYERS["pest_reference_question"]
