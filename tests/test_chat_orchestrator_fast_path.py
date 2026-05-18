"""TICKET-065 — ChatOrchestrator fast-path integration tests.

SQL/rule and RAG fast paths are exercised without a real DB or LLM.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.chat_answer import ChatAnswerResponse, ParsedAnswer
from app.services.chat_orchestrator import ChatOrchestrator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PLANT_ID = uuid.uuid4()
_USER_ID = uuid.uuid4()
_SAMPLE_CONTENT = "[결론] 물주기 필요\n\n[근거] 토양 수분 부족\n\n[행동] 지금 물을 주세요\n\n[주의] 과습 주의"


def _make_session(*, idempotency_result=None, plant=None) -> MagicMock:
    session = MagicMock()
    if plant is not None:
        session.get = AsyncMock(side_effect=[idempotency_result, plant])
    else:
        session.get = AsyncMock(return_value=idempotency_result)
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


def _make_parsed_answer(결론: str = "양호해요.") -> ParsedAnswer:
    return ParsedAnswer(결론=결론, 근거="근거입니다.", 행동="행동하세요.", 주의="주의하세요.")


def _make_healing_result(request_id: uuid.UUID):
    from app.services.llm_port import LLMResponse, ModelMetadata
    from app.services.self_healing_orchestrator import HealingResult

    llm_resp = LLMResponse(
        request_id=request_id,
        content=_SAMPLE_CONTENT,
        prompt_hash="abc123",
        model_metadata=ModelMetadata(model_name="qwen", provider="qwen"),
        input_tokens=10,
        output_tokens=20,
        finish_reason="stop",
    )
    healing = MagicMock(spec=HealingResult)
    healing.final_llm_response = llm_resp
    healing.parsed_answer = ParsedAnswer(결론="물주기 필요", 근거="토양 수분 부족", 행동="지금 물을 주세요", 주의="과습 주의")
    healing.attempts = []
    return healing


# ---------------------------------------------------------------------------
# SQL/rule fast path — basic routing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rule_only_fast_path_no_llm() -> None:
    """상태 어때 → rule_only → fast path, LLM never called."""
    request_id = uuid.uuid4()
    question = "상태 어때"
    fp_answer = _make_parsed_answer("현재 환경이 양호해요.")

    session = _make_session()

    with (
        patch("app.services.chat_orchestrator._CLASSIFIER") as mock_cls,
        patch("app.services.chat_orchestrator.FastPathAnswerService") as mock_fp_cls,
        patch("app.services.chat_orchestrator._LLM_CLIENT") as mock_llm,
    ):
        mock_cls.classify.return_value = ("watering_question", 0.8, "rule")
        mock_fp_cls.return_value.answer = AsyncMock(return_value=fp_answer)

        resp = await ChatOrchestrator().run(
            session,
            plant_id=_PLANT_ID,
            user_id=_USER_ID,
            question=question,
            request_id=request_id,
        )

    mock_llm.complete.assert_not_called()
    assert isinstance(resp, ChatAnswerResponse)
    assert resp.model_name == "fast_path:rule_only"
    assert resp.input_tokens == 0
    assert resp.output_tokens == 0
    assert resp.from_cache is False


@pytest.mark.asyncio
async def test_sql_sensor_fast_path_no_llm() -> None:
    """현재 습도 → sql_sensor → fast path."""
    request_id = uuid.uuid4()
    fp_answer = _make_parsed_answer("현재 습도 65%입니다.")

    session = _make_session()

    with (
        patch("app.services.chat_orchestrator._CLASSIFIER") as mock_cls,
        patch("app.services.chat_orchestrator.FastPathAnswerService") as mock_fp_cls,
        patch("app.services.chat_orchestrator._LLM_CLIENT") as mock_llm,
    ):
        mock_cls.classify.return_value = ("humidity_question", 0.9, "rule")
        mock_fp_cls.return_value.answer = AsyncMock(return_value=fp_answer)

        resp = await ChatOrchestrator().run(
            session,
            plant_id=_PLANT_ID,
            user_id=_USER_ID,
            question="현재 습도 얼마야?",
            request_id=request_id,
        )

    mock_llm.complete.assert_not_called()
    assert resp.model_name == "fast_path:sql_sensor"


@pytest.mark.asyncio
async def test_sql_care_log_fast_path_no_llm() -> None:
    """물 준 기록 → sql_care_log → fast path."""
    request_id = uuid.uuid4()
    fp_answer = _make_parsed_answer("마지막으로 물을 준 것은 3일 전이에요.")

    session = _make_session()

    with (
        patch("app.services.chat_orchestrator._CLASSIFIER") as mock_cls,
        patch("app.services.chat_orchestrator.FastPathAnswerService") as mock_fp_cls,
        patch("app.services.chat_orchestrator._LLM_CLIENT") as mock_llm,
    ):
        mock_cls.classify.return_value = ("watering_question", 0.9, "rule")
        mock_fp_cls.return_value.answer = AsyncMock(return_value=fp_answer)

        resp = await ChatOrchestrator().run(
            session,
            plant_id=_PLANT_ID,
            user_id=_USER_ID,
            question="물 준 기록 보여줘",
            request_id=request_id,
        )

    mock_llm.complete.assert_not_called()
    assert resp.model_name == "fast_path:sql_care_log"


# ---------------------------------------------------------------------------
# SQL/rule fast path — persistence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fast_path_creates_chat_request_and_llm_run_not_healing_log() -> None:
    from app.models.chat_request import ChatRequest
    from app.models.llm_run import LlmRun
    from app.models.llm_self_healing_log import LlmSelfHealingLog

    request_id = uuid.uuid4()
    session = _make_session()

    with (
        patch("app.services.chat_orchestrator._CLASSIFIER") as mock_cls,
        patch("app.services.chat_orchestrator.FastPathAnswerService") as mock_fp_cls,
    ):
        mock_cls.classify.return_value = ("watering_question", 0.8, "rule")
        mock_fp_cls.return_value.answer = AsyncMock(return_value=_make_parsed_answer())

        await ChatOrchestrator().run(
            session,
            plant_id=_PLANT_ID,
            user_id=_USER_ID,
            question="상태 어때",
            request_id=request_id,
        )

    added_types = [type(c.args[0]) for c in session.add.call_args_list]
    assert ChatRequest in added_types
    assert LlmRun in added_types
    assert LlmSelfHealingLog not in added_types


@pytest.mark.asyncio
async def test_fast_path_llm_run_profile_is_fast_path_orchestrator() -> None:
    from app.models.llm_run import LlmRun

    request_id = uuid.uuid4()
    session = _make_session()

    with (
        patch("app.services.chat_orchestrator._CLASSIFIER") as mock_cls,
        patch("app.services.chat_orchestrator.FastPathAnswerService") as mock_fp_cls,
    ):
        mock_cls.classify.return_value = ("watering_question", 0.8, "rule")
        mock_fp_cls.return_value.answer = AsyncMock(return_value=_make_parsed_answer())

        await ChatOrchestrator().run(
            session,
            plant_id=_PLANT_ID,
            user_id=_USER_ID,
            question="상태 어때",
            request_id=request_id,
        )

    llm_runs = [c.args[0] for c in session.add.call_args_list if isinstance(c.args[0], LlmRun)]
    assert len(llm_runs) == 1
    assert llm_runs[0].profile == "fast_path_orchestrator"
    assert llm_runs[0].tokens_in == 0
    assert llm_runs[0].tokens_out == 0


# ---------------------------------------------------------------------------
# SQL/rule fast path failure → fallback to LLM
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fast_path_failure_falls_back_to_llm() -> None:
    """If FastPathAnswerService raises, fall back to LLM path."""
    request_id = uuid.uuid4()
    plant_mock = MagicMock()
    plant_mock.species_profile_id = None
    session = _make_session(plant=plant_mock)
    healing = _make_healing_result(request_id)

    with (
        patch("app.services.chat_orchestrator._CLASSIFIER") as mock_cls,
        patch("app.services.chat_orchestrator.FastPathAnswerService") as mock_fp_cls,
        patch("app.services.chat_orchestrator.RetrievalService") as mock_ret,
        patch("app.services.chat_orchestrator.EvidenceBuilderService") as mock_ev,
        patch("app.services.chat_orchestrator._PROMPT_BUILDER") as mock_pb,
        patch("app.services.chat_orchestrator._HEALER") as mock_healer,
    ):
        mock_cls.classify.return_value = ("watering_question", 0.9, "rule")
        mock_fp_cls.return_value.answer = AsyncMock(side_effect=RuntimeError("db down"))
        mock_ret.return_value.query = AsyncMock(return_value=MagicMock(request_id=uuid.uuid4()))

        from app.domain.evidence import ForwardContext
        ctx = MagicMock(spec=ForwardContext)
        ctx.plant_id = _PLANT_ID
        ctx.user_id = _USER_ID
        ctx.question = "상태 어때"
        ctx.intent = "watering_question"
        ctx.rule_evidence_facts = {}
        ctx.rule_reason_codes = []
        ctx.rule_primary_action = "none"
        ctx.source_coverage = {}
        ctx.retrieved_chunks = []
        ctx.rag_layers = []
        ctx.recent_care_logs = []
        ctx.character = None
        ctx.snapshot = None
        ctx.evidence_hash = "abc"
        mock_ev.return_value.build = AsyncMock(return_value=(ctx, False))

        from app.domain.prompt_build_result import PromptBuildResult
        pr = MagicMock(spec=PromptBuildResult)
        pr.system_prompt = "s"
        pr.user_turn = "상태 어때"
        pr.prompt_hash = "abc"
        pr.guardrails_applied = ()
        mock_pb.build.return_value = pr
        mock_healer.run_with_healing = AsyncMock(return_value=healing)

        resp = await ChatOrchestrator().run(
            session,
            plant_id=_PLANT_ID,
            user_id=_USER_ID,
            question="상태 어때",
            request_id=request_id,
        )

    assert isinstance(resp, ChatAnswerResponse)
    assert resp.model_name == "qwen"
    mock_healer.run_with_healing.assert_called_once()


# ---------------------------------------------------------------------------
# RAG fast path — sufficient
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rag_fast_path_sufficient_no_llm() -> None:
    """키우는 법 → rag_lookup → sufficient RAG → fast path, no LLM."""
    from app.services.rag_fast_path_answer_service import RagFastPathResult

    request_id = uuid.uuid4()
    fp_answer = _make_parsed_answer("관리 지식: 물을 자주 주세요.")
    fp_result = RagFastPathResult(
        answer=fp_answer,
        second_llm_required=False,
        is_sufficient=True,
        chunk_ids_used=[uuid.uuid4()],
    )
    retrieval_mock = MagicMock()
    retrieval_mock.results = []
    session = _make_session()

    with (
        patch("app.services.chat_orchestrator._CLASSIFIER") as mock_cls,
        patch("app.services.chat_orchestrator.RetrievalService") as mock_ret,
        patch("app.services.chat_orchestrator._RAG_FP_SVC") as mock_rag_fp,
        patch("app.services.chat_orchestrator._LLM_CLIENT") as mock_llm,
    ):
        mock_cls.classify.return_value = ("species_care_question", 0.9, "rule")
        mock_ret.return_value.query = AsyncMock(return_value=retrieval_mock)
        mock_rag_fp.evaluate.return_value = fp_result

        resp = await ChatOrchestrator().run(
            session,
            plant_id=_PLANT_ID,
            user_id=_USER_ID,
            question="키우는 법 알려줘",
            request_id=request_id,
        )

    mock_llm.complete.assert_not_called()
    assert isinstance(resp, ChatAnswerResponse)
    assert resp.model_name == "fast_path:rag_lookup"
    assert resp.input_tokens == 0


@pytest.mark.asyncio
async def test_rag_fast_path_pest_reference_only() -> None:
    """병충해 → pest_reference → is_reference_only=True, no LLM."""
    from app.services.rag_fast_path_answer_service import RagFastPathResult

    request_id = uuid.uuid4()
    fp_answer = ParsedAnswer(결론="병충해 정보", 근거="근거", 행동="행동", 주의="전문가 진단 필요")
    fp_result = RagFastPathResult(
        answer=fp_answer,
        second_llm_required=False,
        is_sufficient=True,
        chunk_ids_used=[uuid.uuid4()],
        is_reference_only=True,
        diagnosis_allowed=False,
    )
    retrieval_mock = MagicMock()
    retrieval_mock.results = []
    session = _make_session()

    with (
        patch("app.services.chat_orchestrator._CLASSIFIER") as mock_cls,
        patch("app.services.chat_orchestrator.RetrievalService") as mock_ret,
        patch("app.services.chat_orchestrator._RAG_FP_SVC") as mock_rag_fp,
        patch("app.services.chat_orchestrator._LLM_CLIENT") as mock_llm,
    ):
        mock_cls.classify.return_value = ("pest_reference_question", 0.9, "rule")
        mock_ret.return_value.query = AsyncMock(return_value=retrieval_mock)
        mock_rag_fp.evaluate.return_value = fp_result

        resp = await ChatOrchestrator().run(
            session,
            plant_id=_PLANT_ID,
            user_id=_USER_ID,
            question="병충해 어떻게 해?",
            request_id=request_id,
        )

    mock_llm.complete.assert_not_called()
    assert resp.is_reference_only is True
    assert resp.diagnosis_allowed is False
    assert resp.model_name == "fast_path:pest_reference"


# ---------------------------------------------------------------------------
# RAG fast path — insufficient → LLM path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rag_fast_path_insufficient_falls_through_to_llm() -> None:
    """키우는 법 → rag_lookup → insufficient RAG → LLM called."""
    from app.services.rag_fast_path_answer_service import RagFastPathResult

    request_id = uuid.uuid4()
    retrieval_run_id = uuid.uuid4()
    plant_mock = MagicMock()
    plant_mock.species_profile_id = None
    session = _make_session(plant=plant_mock)
    healing = _make_healing_result(request_id)

    retrieval_mock = MagicMock()
    retrieval_mock.results = []
    retrieval_mock.request_id = retrieval_run_id

    insufficient = RagFastPathResult(answer=None, second_llm_required=True, is_sufficient=False)

    with (
        patch("app.services.chat_orchestrator._CLASSIFIER") as mock_cls,
        patch("app.services.chat_orchestrator.RetrievalService") as mock_ret,
        patch("app.services.chat_orchestrator._RAG_FP_SVC") as mock_rag_fp,
        patch("app.services.chat_orchestrator.EvidenceBuilderService") as mock_ev,
        patch("app.services.chat_orchestrator._PROMPT_BUILDER") as mock_pb,
        patch("app.services.chat_orchestrator._HEALER") as mock_healer,
    ):
        mock_cls.classify.return_value = ("species_care_question", 0.9, "rule")
        mock_ret.return_value.query = AsyncMock(return_value=retrieval_mock)
        mock_rag_fp.evaluate.return_value = insufficient

        from app.domain.evidence import ForwardContext
        ctx = MagicMock(spec=ForwardContext)
        ctx.plant_id = _PLANT_ID
        ctx.user_id = _USER_ID
        ctx.question = "키우는 법 알려줘"
        ctx.intent = "species_care_question"
        ctx.rule_evidence_facts = {}
        ctx.rule_reason_codes = []
        ctx.rule_primary_action = "none"
        ctx.source_coverage = {}
        ctx.retrieved_chunks = []
        ctx.rag_layers = []
        ctx.recent_care_logs = []
        ctx.character = None
        ctx.snapshot = None
        ctx.evidence_hash = "abc"
        mock_ev.return_value.build = AsyncMock(return_value=(ctx, False))

        from app.domain.prompt_build_result import PromptBuildResult
        pr = MagicMock(spec=PromptBuildResult)
        pr.system_prompt = "s"
        pr.user_turn = "키우는 법 알려줘"
        pr.prompt_hash = "abc"
        pr.guardrails_applied = ()
        mock_pb.build.return_value = pr
        mock_healer.run_with_healing = AsyncMock(return_value=healing)

        resp = await ChatOrchestrator().run(
            session,
            plant_id=_PLANT_ID,
            user_id=_USER_ID,
            question="키우는 법 알려줘",
            request_id=request_id,
        )

    mock_healer.run_with_healing.assert_called_once()
    assert resp.model_name == "qwen"


# ---------------------------------------------------------------------------
# audio_uri path skips fast path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audio_uri_skips_fast_path() -> None:
    """audio_uri path does not invoke QuestionRouterService."""
    request_id = uuid.uuid4()
    plant_mock = MagicMock()
    plant_mock.species_profile_id = None
    session = _make_session(plant=plant_mock)
    healing = _make_healing_result(request_id)

    with (
        patch("app.services.chat_orchestrator._CLASSIFIER") as mock_cls,
        patch("app.services.chat_orchestrator._AUDIO_CLIENT") as mock_audio,
        patch("app.services.chat_orchestrator._ROUTER") as mock_router,
        patch("app.services.chat_orchestrator.FastPathAnswerService") as mock_fp_cls,
        patch("app.services.chat_orchestrator.RetrievalService") as mock_ret,
        patch("app.services.chat_orchestrator.EvidenceBuilderService") as mock_ev,
        patch("app.services.chat_orchestrator._PROMPT_BUILDER") as mock_pb,
        patch("app.services.chat_orchestrator._HEALER") as mock_healer,
    ):
        from app.services.audio_port import AudioMetadata, SttResult

        mock_audio.stt = AsyncMock(
            return_value=SttResult(transcript="상태 어때", confidence=0.9, language="ko", source="test")
        )
        mock_audio.tts = AsyncMock(
            return_value=AudioMetadata(audio_uri="out.mp3", format="mp3", sample_rate=16000, duration_seconds=3.0)
        )
        mock_cls.classify.return_value = ("watering_question", 0.9, "rule")
        mock_ret.return_value.query = AsyncMock(return_value=MagicMock(request_id=uuid.uuid4()))

        from app.domain.evidence import ForwardContext
        ctx = MagicMock(spec=ForwardContext)
        ctx.plant_id = _PLANT_ID
        ctx.user_id = _USER_ID
        ctx.question = "상태 어때"
        ctx.intent = "watering_question"
        ctx.rule_evidence_facts = {}
        ctx.rule_reason_codes = []
        ctx.rule_primary_action = "none"
        ctx.source_coverage = {}
        ctx.retrieved_chunks = []
        ctx.rag_layers = []
        ctx.recent_care_logs = []
        ctx.character = None
        ctx.snapshot = None
        ctx.evidence_hash = "abc"
        mock_ev.return_value.build = AsyncMock(return_value=(ctx, False))

        from app.domain.prompt_build_result import PromptBuildResult
        pr = MagicMock(spec=PromptBuildResult)
        pr.system_prompt = "s"
        pr.user_turn = "상태 어때"
        pr.prompt_hash = "abc"
        pr.guardrails_applied = ()
        mock_pb.build.return_value = pr
        mock_healer.run_with_healing = AsyncMock(return_value=healing)

        await ChatOrchestrator().run(
            session,
            plant_id=_PLANT_ID,
            user_id=_USER_ID,
            question=None,
            request_id=request_id,
            audio_uri="input.mp3",
        )

    mock_router.route.assert_not_called()
    mock_fp_cls.assert_not_called()


# ---------------------------------------------------------------------------
# unknown route → LLM called
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_route_calls_llm_not_fast_path() -> None:
    """물주기 알려줘 → unknown route → LLM path, fast path not invoked."""
    request_id = uuid.uuid4()
    plant_mock = MagicMock()
    plant_mock.species_profile_id = None
    session = _make_session(plant=plant_mock)
    healing = _make_healing_result(request_id)

    with (
        patch("app.services.chat_orchestrator._CLASSIFIER") as mock_cls,
        patch("app.services.chat_orchestrator.FastPathAnswerService") as mock_fp_cls,
        patch("app.services.chat_orchestrator.RetrievalService") as mock_ret,
        patch("app.services.chat_orchestrator.EvidenceBuilderService") as mock_ev,
        patch("app.services.chat_orchestrator._PROMPT_BUILDER") as mock_pb,
        patch("app.services.chat_orchestrator._HEALER") as mock_healer,
    ):
        mock_cls.classify.return_value = ("watering_question", 0.9, "rule")
        mock_ret.return_value.query = AsyncMock(return_value=MagicMock(request_id=uuid.uuid4()))

        from app.domain.evidence import ForwardContext
        ctx = MagicMock(spec=ForwardContext)
        ctx.plant_id = _PLANT_ID
        ctx.user_id = _USER_ID
        ctx.question = "물주기 알려줘"
        ctx.intent = "watering_question"
        ctx.rule_evidence_facts = {}
        ctx.rule_reason_codes = []
        ctx.rule_primary_action = "none"
        ctx.source_coverage = {}
        ctx.retrieved_chunks = []
        ctx.rag_layers = []
        ctx.recent_care_logs = []
        ctx.character = None
        ctx.snapshot = None
        ctx.evidence_hash = "abc"
        mock_ev.return_value.build = AsyncMock(return_value=(ctx, False))

        from app.domain.prompt_build_result import PromptBuildResult
        pr = MagicMock(spec=PromptBuildResult)
        pr.system_prompt = "s"
        pr.user_turn = "물주기 알려줘"
        pr.prompt_hash = "abc"
        pr.guardrails_applied = ()
        mock_pb.build.return_value = pr
        mock_healer.run_with_healing = AsyncMock(return_value=healing)

        resp = await ChatOrchestrator().run(
            session,
            plant_id=_PLANT_ID,
            user_id=_USER_ID,
            question="물주기 알려줘",
            request_id=request_id,
        )

    mock_fp_cls.assert_not_called()
    mock_healer.run_with_healing.assert_called_once()
    assert resp.model_name == "qwen"


# ---------------------------------------------------------------------------
# Cached fast-path response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cached_fast_path_response_loads_correctly() -> None:
    """Duplicate request_id with fast-path status returns cached answer."""
    from app.models.chat_request import ChatRequest
    from app.models.llm_run import LlmRun

    request_id = uuid.uuid4()
    now = datetime.now(UTC)

    existing_chat = MagicMock(spec=ChatRequest)
    existing_chat.id = request_id
    existing_chat.plant_id = _PLANT_ID
    existing_chat.status = "sql_sensor"
    existing_chat.created_at = now

    existing_llm_run = MagicMock(spec=LlmRun)
    existing_llm_run.response_text = "[결론] 센서 데이터\n\n[근거] 근거\n\n[행동] 행동\n\n[주의] 주의"
    existing_llm_run.prompt_hash = "fp_hash"
    existing_llm_run.model_name = "fast_path:sql_sensor"
    existing_llm_run.tokens_in = 0
    existing_llm_run.tokens_out = 0

    session = _make_session(idempotency_result=existing_chat)
    mock_scalar = MagicMock()
    mock_scalar.scalar_one_or_none.return_value = existing_llm_run
    session.execute = AsyncMock(return_value=mock_scalar)

    resp = await ChatOrchestrator().run(
        session,
        plant_id=_PLANT_ID,
        user_id=_USER_ID,
        question="현재 습도",
        request_id=request_id,
    )

    assert resp.from_cache is True
    assert resp.model_name == "fast_path:sql_sensor"
    assert resp.input_tokens == 0
    session.add.assert_not_called()


# ---------------------------------------------------------------------------
# Module-level constant checks
# ---------------------------------------------------------------------------


def test_sql_rule_routes_constant() -> None:
    from app.services.chat_orchestrator import _SQL_RULE_ROUTES

    assert "rule_only" in _SQL_RULE_ROUTES
    assert "sql_sensor" in _SQL_RULE_ROUTES
    assert "sql_care_log" in _SQL_RULE_ROUTES


def test_rag_fast_routes_constant() -> None:
    from app.services.chat_orchestrator import _RAG_FAST_ROUTES

    assert "rag_lookup" in _RAG_FAST_ROUTES
    assert "pest_reference" in _RAG_FAST_ROUTES


def test_rag_route_layers_pest_reference() -> None:
    from app.services.chat_orchestrator import _RAG_ROUTE_TO_LAYERS

    assert "pest_disease_reference" in _RAG_ROUTE_TO_LAYERS["pest_reference"]


def test_rag_route_layers_rag_lookup() -> None:
    from app.services.chat_orchestrator import _RAG_ROUTE_TO_LAYERS

    assert "care_knowledge" in _RAG_ROUTE_TO_LAYERS["rag_lookup"]
    assert "species_profile" in _RAG_ROUTE_TO_LAYERS["rag_lookup"]
