"""TICKET-034 — Chat evaluation service tests.

Covers:
  - assign_ab_group (deterministic A/B routing)
  - compute_faithfulness (evidence grounding)
  - compute_answer_relevance (keyword overlap)
  - compute_ground_truth_similarity (required keyword coverage)
  - find_matching_ground_truth (DB query with intent + keyword matching)
  - evaluate_and_save (end-to-end orchestration + DB persistence)
  - AuditRepository _assemble (evaluation field propagation)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.evaluation import (
    EvaluationMetrics,
    EvaluationResult,
    GroundTruthSpec,
)
from app.domain.evidence import ChunkEvidence, ForwardContext
from app.schemas.chat_answer import ParsedAnswer
from app.services.chat_evaluation_service import (
    assign_ab_group,
    compute_answer_relevance,
    compute_faithfulness,
    compute_ground_truth_similarity,
)

# ---------------------------------------------------------------------------
# Test fixtures / builders
# ---------------------------------------------------------------------------

_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)


def _parsed(
    결론: str = "물이 부족합니다.",
    근거: str = "토양 수분이 낮습니다.",
    행동: str = "물을 지금 주세요.",
    주의: str = "과습에 주의하세요.",
) -> ParsedAnswer:
    return ParsedAnswer(결론=결론, 근거=근거, 행동=행동, 주의=주의)


def _ctx(
    rule_reason_codes: list[str] | None = None,
    rule_primary_action: str = "water_now",
    retrieved_chunks: list[ChunkEvidence] | None = None,
) -> ForwardContext:
    plant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    return ForwardContext.build(
        plant_id=plant_id,
        user_id=user_id,
        question="물 주는 시기가 언제야?",
        intent="watering_question",
        rag_layers=["care_knowledge"],
        character=None,
        snapshot=None,
        recent_care_logs=[],
        rule_evidence_facts={},
        rule_reason_codes=rule_reason_codes or [],
        rule_primary_action=rule_primary_action,
        retrieved_chunks=retrieved_chunks or [],
        source_coverage={},
    )


def _chunk(kind: str = "care_knowledge", text: str = "선인장은 건조한 환경을 좋아합니다.") -> ChunkEvidence:
    return ChunkEvidence(
        chunk_document_id=str(uuid.uuid4()),
        plant_knowledge_id=str(uuid.uuid4()),
        chunk_kind=kind,
        chunk_text=text,
        similarity_score=0.9,
        rank=1,
    )


def _gt_entry_mock(
    intent: str = "watering_question",
    question_keywords: list[str] | None = None,
    expected_answer: str = "토양이 건조할 때 물을 주세요.",
    required_keywords: list[str] | None = None,
) -> MagicMock:
    m = MagicMock()
    m.id = uuid.uuid4()
    m.intent = intent
    m.question_keywords = question_keywords or ["물주기", "시기"]
    m.expected_answer = expected_answer
    m.required_keywords = required_keywords or ["토양", "물"]
    m.created_at = _NOW
    return m


def _make_session() -> AsyncMock:
    session = AsyncMock()
    session.get = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


def _exec_scalars(items: list) -> MagicMock:
    result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = items
    result.scalars.return_value = scalars_mock
    return result


def _exec_scalar_one(obj) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = obj
    return result


# ---------------------------------------------------------------------------
# assign_ab_group — deterministic routing
# ---------------------------------------------------------------------------


def test_ab_group_is_control_or_experiment() -> None:
    group = assign_ab_group(uuid.uuid4())
    assert group in ("control", "experiment")


def test_ab_group_deterministic_same_id() -> None:
    rid = uuid.uuid4()
    assert assign_ab_group(rid) == assign_ab_group(rid)


def test_ab_group_even_last_byte_is_control() -> None:
    # Construct a UUID whose last byte is 0 (even → control)
    raw = bytearray(uuid.uuid4().bytes)
    raw[-1] = 0
    rid = uuid.UUID(bytes=bytes(raw))
    assert assign_ab_group(rid) == "control"


def test_ab_group_odd_last_byte_is_experiment() -> None:
    raw = bytearray(uuid.uuid4().bytes)
    raw[-1] = 1
    rid = uuid.UUID(bytes=bytes(raw))
    assert assign_ab_group(rid) == "experiment"


def test_ab_group_distribution_roughly_balanced() -> None:
    groups = [assign_ab_group(uuid.uuid4()) for _ in range(200)]
    control_count = groups.count("control")
    assert 70 <= control_count <= 130  # roughly 50%


# ---------------------------------------------------------------------------
# compute_faithfulness
# ---------------------------------------------------------------------------


def test_faithfulness_no_evidence_returns_one() -> None:
    ctx = _ctx(rule_reason_codes=[], retrieved_chunks=[])
    assert compute_faithfulness(_parsed(), ctx) == 1.0


def test_faithfulness_rule_code_present_in_answer() -> None:
    # answer text contains "soil_dry" implicitly via 토양
    # Use a code that IS in the answer
    ctx = _ctx(rule_reason_codes=["토양"], retrieved_chunks=[])
    score = compute_faithfulness(_parsed(근거="토양 수분이 낮습니다."), ctx)
    assert score > 0.0


def test_faithfulness_rule_code_absent_reduces_score() -> None:
    ctx = _ctx(rule_reason_codes=["xyzzy_missing_code"], retrieved_chunks=[])
    score = compute_faithfulness(_parsed(), ctx)
    assert score == pytest.approx(0.0, abs=0.01)


def test_faithfulness_chunk_kind_present() -> None:
    chunk = _chunk(kind="care_knowledge", text="물주기 관련 지식입니다.")
    ctx = _ctx(retrieved_chunks=[chunk])
    # answer text: "care_knowledge" not in Korean answer, but chunk text word "물주기" is
    answer = _parsed(근거="물주기 방법에 대해 설명합니다.")
    score = compute_faithfulness(answer, ctx)
    assert score > 0.0


def test_faithfulness_chunk_kind_absent() -> None:
    chunk = _chunk(kind="xyzzy_unknown_kind", text="완전히다른내용입니다.")
    ctx = _ctx(retrieved_chunks=[chunk])
    score = compute_faithfulness(_parsed(), ctx)
    # chunk kind not in answer, chunk content words not in answer
    assert score == pytest.approx(0.0, abs=0.01)


def test_faithfulness_combined_partial_score() -> None:
    # 1 of 2 codes present → 0.5 * 0.5 = 0.25 for codes weight
    ctx = _ctx(
        rule_reason_codes=["토양", "completely_absent"],
        retrieved_chunks=[],
    )
    answer = _parsed(근거="토양 수분이 낮습니다.")
    score = compute_faithfulness(answer, ctx)
    # codes weight = 0.5, hit rate = 0.5 → 0.25; chunk weight = 0 → total / 0.5 = 0.5
    assert 0.0 < score <= 1.0


def test_faithfulness_bounded_zero_to_one() -> None:
    ctx = _ctx(rule_reason_codes=["a", "b", "c"], retrieved_chunks=[_chunk()])
    score = compute_faithfulness(_parsed(), ctx)
    assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# compute_answer_relevance
# ---------------------------------------------------------------------------


def test_relevance_all_keywords_in_answer() -> None:
    question = "물주기"
    answer = _parsed(결론="물주기 필요합니다.", 근거="", 행동="", 주의="")
    score = compute_answer_relevance(question, answer)
    assert score == pytest.approx(1.0)


def test_relevance_no_keywords_in_answer() -> None:
    question = "xyzzy플랜트가격질문"
    answer = _parsed()
    score = compute_answer_relevance(question, answer)
    assert score == pytest.approx(0.0)


def test_relevance_partial_overlap() -> None:
    question = "물주기 시기 확인"
    answer = _parsed(결론="물주기가 필요합니다.", 근거="현재 시기에 맞게 조절하세요.", 행동="물을 주세요.", 주의="없음입니다.")
    score = compute_answer_relevance(question, answer)
    assert 0.0 < score <= 1.0


def test_relevance_empty_question() -> None:
    score = compute_answer_relevance("", _parsed())
    assert score == pytest.approx(0.0)


def test_relevance_bounded() -> None:
    question = "물주기 시기가 언제인지 알고 싶어요"
    score = compute_answer_relevance(question, _parsed())
    assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# compute_ground_truth_similarity
# ---------------------------------------------------------------------------


def test_gt_similarity_no_spec_returns_zero() -> None:
    assert compute_ground_truth_similarity(_parsed(), None) == pytest.approx(0.0)


def test_gt_similarity_empty_required_keywords_returns_zero() -> None:
    spec = GroundTruthSpec(
        id=uuid.uuid4(),
        question_keywords=[],
        expected_answer="",
        required_keywords=[],
        intent="watering_question",
    )
    assert compute_ground_truth_similarity(_parsed(), spec) == pytest.approx(0.0)


def test_gt_similarity_all_required_keywords_present() -> None:
    spec = GroundTruthSpec(
        id=uuid.uuid4(),
        question_keywords=["물주기"],
        expected_answer="토양이 건조할 때 물을 주세요.",
        required_keywords=["물"],
        intent="watering_question",
    )
    answer = _parsed(행동="지금 물을 충분히 주세요.")
    score = compute_ground_truth_similarity(answer, spec)
    assert score == pytest.approx(1.0)


def test_gt_similarity_none_present_returns_zero() -> None:
    spec = GroundTruthSpec(
        id=uuid.uuid4(),
        question_keywords=[],
        expected_answer="",
        required_keywords=["xyzzy_absent", "zzaabb_absent"],
        intent="watering_question",
    )
    score = compute_ground_truth_similarity(_parsed(), spec)
    assert score == pytest.approx(0.0)


def test_gt_similarity_partial() -> None:
    spec = GroundTruthSpec(
        id=uuid.uuid4(),
        question_keywords=[],
        expected_answer="",
        required_keywords=["토양", "xyzzy_missing"],
        intent="watering_question",
    )
    answer = _parsed(근거="토양 수분이 낮습니다.")
    score = compute_ground_truth_similarity(answer, spec)
    assert score == pytest.approx(0.5)


def test_gt_similarity_bounded() -> None:
    spec = GroundTruthSpec(
        id=uuid.uuid4(),
        question_keywords=[],
        expected_answer="",
        required_keywords=["물", "토양", "빛"],
        intent="watering_question",
    )
    score = compute_ground_truth_similarity(_parsed(), spec)
    assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# find_matching_ground_truth (session-mocked)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_returns_none_when_no_entries() -> None:
    from app.services.chat_evaluation_service import ChatEvaluationService

    session = _make_session()
    session.execute = AsyncMock(return_value=_exec_scalars([]))
    svc = ChatEvaluationService(session)
    result = await svc.find_matching_ground_truth("물 주기가 언제야?", "watering_question")
    assert result is None


@pytest.mark.asyncio
async def test_find_returns_spec_when_single_entry() -> None:
    from app.services.chat_evaluation_service import ChatEvaluationService

    entry = _gt_entry_mock(question_keywords=["물주기", "시기"])
    session = _make_session()
    session.execute = AsyncMock(return_value=_exec_scalars([entry]))
    svc = ChatEvaluationService(session)
    result = await svc.find_matching_ground_truth("물주기 시기가 언제야?", "watering_question")
    assert isinstance(result, GroundTruthSpec)
    assert result.id == entry.id


@pytest.mark.asyncio
async def test_find_picks_best_keyword_overlap() -> None:
    from app.services.chat_evaluation_service import ChatEvaluationService

    low = _gt_entry_mock(question_keywords=["빛", "조도"])       # 0 overlap
    high = _gt_entry_mock(question_keywords=["물주기", "시기"])   # 2 overlaps
    session = _make_session()
    session.execute = AsyncMock(return_value=_exec_scalars([low, high]))
    svc = ChatEvaluationService(session)
    result = await svc.find_matching_ground_truth("물주기 시기가 언제야?", "watering_question")
    assert result is not None
    assert result.id == high.id


@pytest.mark.asyncio
async def test_find_spec_has_correct_fields() -> None:
    from app.services.chat_evaluation_service import ChatEvaluationService

    entry = _gt_entry_mock(
        required_keywords=["토양", "물"],
        expected_answer="토양이 건조할 때 물을 주세요.",
        intent="watering_question",
    )
    session = _make_session()
    session.execute = AsyncMock(return_value=_exec_scalars([entry]))
    svc = ChatEvaluationService(session)
    result = await svc.find_matching_ground_truth("물주기", "watering_question")
    assert result is not None
    assert result.required_keywords == ["토양", "물"]
    assert result.expected_answer == "토양이 건조할 때 물을 주세요."
    assert result.intent == "watering_question"


# ---------------------------------------------------------------------------
# evaluate_and_save (end-to-end, session-mocked)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_and_save_returns_evaluation_result() -> None:
    from app.services.chat_evaluation_service import ChatEvaluationService

    session = _make_session()
    session.execute = AsyncMock(return_value=_exec_scalars([]))  # no ground truth
    svc = ChatEvaluationService(session)
    result = await svc.evaluate_and_save(
        request_id=uuid.uuid4(),
        question="물주기 시기가 언제야?",
        answer=_parsed(),
        ctx=_ctx(),
        intent="watering_question",
    )
    assert isinstance(result, EvaluationResult)


@pytest.mark.asyncio
async def test_evaluate_and_save_persists_row() -> None:
    from app.models.chat_evaluation import ChatEvaluationResult
    from app.services.chat_evaluation_service import ChatEvaluationService

    session = _make_session()
    session.execute = AsyncMock(return_value=_exec_scalars([]))
    svc = ChatEvaluationService(session)
    await svc.evaluate_and_save(
        request_id=uuid.uuid4(),
        question="물주기 시기",
        answer=_parsed(),
        ctx=_ctx(),
        intent="watering_question",
    )
    added_objects = [call.args[0] for call in session.add.call_args_list]
    assert any(isinstance(o, ChatEvaluationResult) for o in added_objects)


@pytest.mark.asyncio
async def test_evaluate_and_save_ab_group_matches_assign() -> None:
    from app.services.chat_evaluation_service import ChatEvaluationService

    request_id = uuid.uuid4()
    expected_group = assign_ab_group(request_id)

    session = _make_session()
    session.execute = AsyncMock(return_value=_exec_scalars([]))
    svc = ChatEvaluationService(session)
    result = await svc.evaluate_and_save(
        request_id=request_id,
        question="물주기",
        answer=_parsed(),
        ctx=_ctx(),
        intent="watering_question",
    )
    assert result.ab_test_group == expected_group


@pytest.mark.asyncio
async def test_evaluate_and_save_no_match_sets_null_id() -> None:
    from app.services.chat_evaluation_service import ChatEvaluationService

    session = _make_session()
    session.execute = AsyncMock(return_value=_exec_scalars([]))
    svc = ChatEvaluationService(session)
    result = await svc.evaluate_and_save(
        request_id=uuid.uuid4(),
        question="물주기",
        answer=_parsed(),
        ctx=_ctx(),
        intent="watering_question",
    )
    assert result.matched_ground_truth_id is None


@pytest.mark.asyncio
async def test_evaluate_and_save_with_match_sets_gt_id() -> None:
    from app.services.chat_evaluation_service import ChatEvaluationService

    entry = _gt_entry_mock(question_keywords=["물주기"])
    session = _make_session()
    session.execute = AsyncMock(return_value=_exec_scalars([entry]))
    svc = ChatEvaluationService(session)
    result = await svc.evaluate_and_save(
        request_id=uuid.uuid4(),
        question="물주기 시기",
        answer=_parsed(),
        ctx=_ctx(),
        intent="watering_question",
    )
    assert result.matched_ground_truth_id == entry.id


@pytest.mark.asyncio
async def test_evaluate_and_save_metrics_bounded() -> None:
    from app.services.chat_evaluation_service import ChatEvaluationService

    session = _make_session()
    session.execute = AsyncMock(return_value=_exec_scalars([]))
    svc = ChatEvaluationService(session)
    result = await svc.evaluate_and_save(
        request_id=uuid.uuid4(),
        question="물주기 시기",
        answer=_parsed(),
        ctx=_ctx(rule_reason_codes=["토양"], retrieved_chunks=[_chunk()]),
        intent="watering_question",
    )
    m = result.metrics
    assert 0.0 <= m.faithfulness <= 1.0
    assert 0.0 <= m.answer_relevance <= 1.0
    assert 0.0 <= m.ground_truth_similarity <= 1.0


@pytest.mark.asyncio
async def test_evaluate_and_save_flushes_session() -> None:
    from app.services.chat_evaluation_service import ChatEvaluationService

    session = _make_session()
    session.execute = AsyncMock(return_value=_exec_scalars([]))
    svc = ChatEvaluationService(session)
    await svc.evaluate_and_save(
        request_id=uuid.uuid4(),
        question="물주기",
        answer=_parsed(),
        ctx=_ctx(),
        intent="watering_question",
    )
    session.flush.assert_called_once()


# ---------------------------------------------------------------------------
# AuditRepository _assemble — evaluation field propagation
# ---------------------------------------------------------------------------


def _make_eval_row_mock() -> MagicMock:
    m = MagicMock()
    m.ab_test_group = "experiment"
    m.faithfulness = 0.8
    m.answer_relevance = 0.7
    m.ground_truth_similarity = 0.6
    m.matched_ground_truth_id = uuid.uuid4()
    return m


def _make_chat_mock() -> MagicMock:
    m = MagicMock()
    m.id = uuid.uuid4()
    m.plant_id = uuid.uuid4()
    m.question = "물 주는 시기?"
    m.status = "watering_question"
    m.user_id = uuid.uuid4()
    m.created_at = _NOW
    return m


def _make_llm_run_mock() -> MagicMock:
    m = MagicMock()
    import hashlib
    text = "테스트 프롬프트"
    m.prompt_text = text
    m.prompt_hash = hashlib.sha256(text.encode()).hexdigest()
    m.response_text = "[결론] 물 주세요."
    m.model_name = "mock-gpt"
    m.tokens_in = 100
    m.tokens_out = 50
    m.latency_ms = 200
    return m


def test_assemble_with_eval_row_sets_evaluation() -> None:
    from app.repositories.audit_repository import _assemble
    from app.schemas.audit_view import EvaluationSummary

    chat = _make_chat_mock()
    run = _make_llm_run_mock()
    eval_row = _make_eval_row_mock()

    view = _assemble(chat, run, None, [], eval_row)

    assert view.evaluation is not None
    assert isinstance(view.evaluation, EvaluationSummary)
    assert view.evaluation.ab_test_group == "experiment"
    assert view.evaluation.faithfulness == pytest.approx(0.8)
    assert view.evaluation.answer_relevance == pytest.approx(0.7)
    assert view.evaluation.ground_truth_similarity == pytest.approx(0.6)


def test_assemble_without_eval_row_evaluation_is_none() -> None:
    from app.repositories.audit_repository import _assemble

    view = _assemble(_make_chat_mock(), _make_llm_run_mock(), None, [])
    assert view.evaluation is None


def test_assemble_eval_matched_gt_id_propagated() -> None:
    from app.repositories.audit_repository import _assemble

    eval_row = _make_eval_row_mock()
    expected_id = eval_row.matched_ground_truth_id
    view = _assemble(_make_chat_mock(), _make_llm_run_mock(), None, [], eval_row)
    assert view.evaluation is not None
    assert view.evaluation.matched_ground_truth_id == expected_id
