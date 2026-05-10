"""TICKET-022 — Evidence persistence & audit query tests.

Tests cover:
  - _check_hash (prompt integrity helper)
  - _assemble (view builder from model mocks)
  - AuditRepository.get_chat_run_evidence (session-mocked)
  - AuditQueryService.get_evidence (error propagation)
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.audit_repository import _assemble, _check_hash
from app.schemas.audit_view import ChatRunEvidenceView, ChunkSummary, SnapshotSummary
from app.services.audit_query_service import AuditQueryService, ChatRunNotFoundError

# ---------------------------------------------------------------------------
# Constants shared across tests
# ---------------------------------------------------------------------------

_SAMPLE_PROMPT = "# 식물 관리 전문가 AI\n\n테스트 시스템 프롬프트"
_SAMPLE_HASH = hashlib.sha256(_SAMPLE_PROMPT.encode("utf-8")).hexdigest()
_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Mock builders
# ---------------------------------------------------------------------------


def _make_session() -> AsyncMock:
    session = AsyncMock()
    session.get = AsyncMock()
    session.execute = AsyncMock()
    return session


def _chat_mock(
    *,
    request_id: uuid.UUID | None = None,
    plant_id: uuid.UUID | None = None,
    question: str = "물 주는 시기가 언제야?",
    intent: str = "watering_question",
) -> MagicMock:
    m = MagicMock()
    m.id = request_id or uuid.uuid4()
    m.plant_id = plant_id or uuid.uuid4()
    m.question = question
    m.status = intent
    m.user_id = uuid.uuid4()
    m.created_at = _NOW
    return m


def _llm_run_mock(
    *,
    prompt_text: str = _SAMPLE_PROMPT,
    prompt_hash: str = _SAMPLE_HASH,
    response_text: str = "[결론] 물 주세요.\n\n[근거] 흙이 건조합니다.",
    model_name: str = "mock-gpt",
    tokens_in: int = 120,
    tokens_out: int = 60,
    latency_ms: int = 300,
) -> MagicMock:
    m = MagicMock()
    m.prompt_text = prompt_text
    m.prompt_hash = prompt_hash
    m.response_text = response_text
    m.model_name = model_name
    m.tokens_in = tokens_in
    m.tokens_out = tokens_out
    m.latency_ms = latency_ms
    return m


def _bundle_mock(evidence_hash: str = "abc123def456") -> MagicMock:
    m = MagicMock()
    m.evidence_hash = evidence_hash
    m.rag_layers = ["care_knowledge", "species_profile"]
    m.bundle_json = {
        "snapshot": {
            "window": "1h",
            "temperature_avg_c": 22.5,
            "humidity_avg_pct": 60.0,
            "light_avg_lux": 500.0,
            "soil_moisture_avg_pct": None,
        },
        "rule_primary_action": "water_now",
        "rule_reason_codes": ["soil_dry"],
        "rule_evidence_facts": {"soil_moisture_pct": 22.0},
        "retrieved_chunks": [
            {
                "chunk_document_id": str(uuid.uuid4()),
                "chunk_kind": "care_knowledge",
                "chunk_text": "선인장은 건조한 환경을 좋아합니다.",
                "similarity_score": 0.87,
                "rank": 1,
            }
        ],
        "source_coverage": {"care_knowledge": True, "species_profile": False},
    }
    return m


def _exec_result(obj: object | None) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = obj
    return result


# ---------------------------------------------------------------------------
# _check_hash (unit)
# ---------------------------------------------------------------------------


def test_check_hash_valid() -> None:
    assert _check_hash(_SAMPLE_PROMPT, _SAMPLE_HASH) is True


def test_check_hash_wrong_hash() -> None:
    assert _check_hash(_SAMPLE_PROMPT, "not_the_right_hash") is False


def test_check_hash_empty_prompt() -> None:
    assert _check_hash("", _SAMPLE_HASH) is False


def test_check_hash_none_hash() -> None:
    assert _check_hash(_SAMPLE_PROMPT, None) is False


# ---------------------------------------------------------------------------
# _assemble (unit) — view construction from model mocks
# ---------------------------------------------------------------------------


def test_assemble_basic_fields() -> None:
    chat = _chat_mock()
    run = _llm_run_mock()
    view = _assemble(chat, run, None)
    assert view.request_id == chat.id
    assert view.question == chat.question
    assert view.intent == chat.status


def test_assemble_prompt_text_and_hash() -> None:
    chat = _chat_mock()
    run = _llm_run_mock()
    view = _assemble(chat, run, None)
    assert view.prompt_text == _SAMPLE_PROMPT
    assert view.prompt_hash == _SAMPLE_HASH


def test_assemble_is_prompt_hash_valid_true() -> None:
    view = _assemble(_chat_mock(), _llm_run_mock(), None)
    assert view.is_prompt_hash_valid is True


def test_assemble_is_prompt_hash_valid_false_when_tampered() -> None:
    run = _llm_run_mock(prompt_hash="tampered_hash_value")
    view = _assemble(_chat_mock(), run, None)
    assert view.is_prompt_hash_valid is False


def test_assemble_no_bundle_has_empty_evidence() -> None:
    view = _assemble(_chat_mock(), _llm_run_mock(), None)
    assert view.evidence_hash is None
    assert view.sensor_snapshot is None
    assert view.rule_primary_action is None
    assert view.rule_reason_codes == []
    assert view.rule_evidence_facts == {}
    assert view.retrieved_chunks == []
    assert view.source_coverage == {}
    assert view.rag_layers == []


def test_assemble_with_bundle_evidence_hash() -> None:
    bundle = _bundle_mock(evidence_hash="hash_value_42")
    view = _assemble(_chat_mock(), _llm_run_mock(), bundle)
    assert view.evidence_hash == "hash_value_42"


def test_assemble_with_bundle_snapshot() -> None:
    bundle = _bundle_mock()
    view = _assemble(_chat_mock(), _llm_run_mock(), bundle)
    assert isinstance(view.sensor_snapshot, SnapshotSummary)
    assert view.sensor_snapshot.window == "1h"
    assert view.sensor_snapshot.temperature_avg_c == 22.5
    assert view.sensor_snapshot.humidity_avg_pct == 60.0


def test_assemble_with_bundle_rule_fields() -> None:
    bundle = _bundle_mock()
    view = _assemble(_chat_mock(), _llm_run_mock(), bundle)
    assert view.rule_primary_action == "water_now"
    assert view.rule_reason_codes == ["soil_dry"]
    assert view.rule_evidence_facts == {"soil_moisture_pct": 22.0}


def test_assemble_with_bundle_retrieved_chunks() -> None:
    bundle = _bundle_mock()
    view = _assemble(_chat_mock(), _llm_run_mock(), bundle)
    assert len(view.retrieved_chunks) == 1
    chunk = view.retrieved_chunks[0]
    assert isinstance(chunk, ChunkSummary)
    assert chunk.chunk_kind == "care_knowledge"
    assert chunk.similarity_score == pytest.approx(0.87)
    assert chunk.rank == 1


def test_assemble_with_bundle_source_coverage() -> None:
    bundle = _bundle_mock()
    view = _assemble(_chat_mock(), _llm_run_mock(), bundle)
    assert view.source_coverage == {"care_knowledge": True, "species_profile": False}


def test_assemble_with_bundle_rag_layers() -> None:
    bundle = _bundle_mock()
    view = _assemble(_chat_mock(), _llm_run_mock(), bundle)
    assert set(view.rag_layers) == {"care_knowledge", "species_profile"}


def test_assemble_no_llm_run_defaults_to_empty_strings() -> None:
    view = _assemble(_chat_mock(), None, None)
    assert view.prompt_text == ""
    assert view.prompt_hash == ""
    assert view.response_text == ""
    assert view.model_name == ""
    assert view.input_tokens == 0
    assert view.output_tokens == 0
    assert view.latency_ms == 0
    assert view.is_prompt_hash_valid is False


def test_assemble_tokens_and_latency() -> None:
    run = _llm_run_mock(tokens_in=200, tokens_out=80, latency_ms=450)
    view = _assemble(_chat_mock(), run, None)
    assert view.input_tokens == 200
    assert view.output_tokens == 80
    assert view.latency_ms == 450


# ---------------------------------------------------------------------------
# AuditRepository.get_chat_run_evidence (session-mocked)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_repo_returns_none_when_chat_not_found() -> None:
    from app.repositories.audit_repository import AuditRepository

    session = _make_session()
    session.get = AsyncMock(return_value=None)
    repo = AuditRepository(session)
    result = await repo.get_chat_run_evidence(uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_repo_returns_view_with_evidence() -> None:
    from app.repositories.audit_repository import AuditRepository

    request_id = uuid.uuid4()
    plant_id = uuid.uuid4()
    chat = _chat_mock(request_id=request_id, plant_id=plant_id)
    run = _llm_run_mock()
    bundle = _bundle_mock()

    session = _make_session()
    session.get = AsyncMock(return_value=chat)
    session.execute = AsyncMock(
        side_effect=[_exec_result(run), _exec_result(bundle)]
    )

    repo = AuditRepository(session)
    view = await repo.get_chat_run_evidence(request_id)

    assert view is not None
    assert view.request_id == request_id
    assert view.evidence_hash == "abc123def456"
    assert view.sensor_snapshot is not None


@pytest.mark.asyncio
async def test_repo_skips_bundle_for_companion_intent() -> None:
    from app.repositories.audit_repository import AuditRepository

    request_id = uuid.uuid4()
    chat = _chat_mock(request_id=request_id, intent="companion_plant_question")
    run = _llm_run_mock()

    session = _make_session()
    session.get = AsyncMock(return_value=chat)
    session.execute = AsyncMock(side_effect=[_exec_result(run)])

    repo = AuditRepository(session)
    view = await repo.get_chat_run_evidence(request_id)

    assert view is not None
    assert view.intent == "companion_plant_question"
    assert view.evidence_hash is None
    assert view.sensor_snapshot is None
    # execute called once only (LlmRun), no second call for EvidenceBundle
    assert session.execute.call_count == 1


@pytest.mark.asyncio
async def test_repo_view_created_at_matches_chat() -> None:
    from app.repositories.audit_repository import AuditRepository

    request_id = uuid.uuid4()
    chat = _chat_mock(request_id=request_id)
    run = _llm_run_mock()
    bundle = _bundle_mock()

    session = _make_session()
    session.get = AsyncMock(return_value=chat)
    session.execute = AsyncMock(side_effect=[_exec_result(run), _exec_result(bundle)])

    repo = AuditRepository(session)
    view = await repo.get_chat_run_evidence(request_id)

    assert view.created_at == _NOW


@pytest.mark.asyncio
async def test_repo_no_bundle_match_returns_view_without_evidence() -> None:
    from app.repositories.audit_repository import AuditRepository

    request_id = uuid.uuid4()
    chat = _chat_mock(request_id=request_id)
    run = _llm_run_mock()

    session = _make_session()
    session.get = AsyncMock(return_value=chat)
    # LlmRun found, EvidenceBundle not found
    session.execute = AsyncMock(side_effect=[_exec_result(run), _exec_result(None)])

    repo = AuditRepository(session)
    view = await repo.get_chat_run_evidence(request_id)

    assert view is not None
    assert view.evidence_hash is None
    assert view.rule_reason_codes == []


# ---------------------------------------------------------------------------
# AuditQueryService.get_evidence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_service_raises_not_found_when_missing() -> None:
    session = _make_session()
    session.get = AsyncMock(return_value=None)

    svc = AuditQueryService(session)
    with pytest.raises(ChatRunNotFoundError):
        await svc.get_evidence(uuid.uuid4())


@pytest.mark.asyncio
async def test_service_returns_view_when_found() -> None:
    request_id = uuid.uuid4()
    chat = _chat_mock(request_id=request_id)
    run = _llm_run_mock()
    bundle = _bundle_mock()

    session = _make_session()
    session.get = AsyncMock(return_value=chat)
    session.execute = AsyncMock(side_effect=[_exec_result(run), _exec_result(bundle)])

    svc = AuditQueryService(session)
    view = await svc.get_evidence(request_id)

    assert isinstance(view, ChatRunEvidenceView)
    assert view.request_id == request_id


@pytest.mark.asyncio
async def test_service_integrity_flag_propagated() -> None:
    request_id = uuid.uuid4()
    chat = _chat_mock(request_id=request_id)
    run = _llm_run_mock(prompt_hash="wrong_hash")

    session = _make_session()
    session.get = AsyncMock(return_value=chat)
    session.execute = AsyncMock(side_effect=[_exec_result(run), _exec_result(None)])

    svc = AuditQueryService(session)
    view = await svc.get_evidence(request_id)

    assert view.is_prompt_hash_valid is False
