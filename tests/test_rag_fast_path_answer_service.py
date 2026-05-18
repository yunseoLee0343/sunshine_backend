"""TICKET-064 — RagFastPathAnswerService unit tests.

All tests are pure/synchronous — no DB, no LLM, no network.
"""

from __future__ import annotations

import uuid

import pytest

from app.domain.question_router import QuestionRouteDecision
from app.domain.retrieval import RetrievedChunkResult
from app.schemas.chat_answer import ParsedAnswer
from app.services.pest_reference_guardrail import REQUIRED_DISCLAIMER
from app.services.rag_fast_path_answer_service import (
    FAST_PATH_KINDS,
    RagFastPathAnswerService,
    RagFastPathResult,
    check_sufficiency,
    chunks_to_answer,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _chunk(
    kind: str = "care_requirement",
    text: str = "이 식물은 물을 자주 주지 않아도 됩니다. 토양 표면이 건조할 때 물을 주세요.",
    score: float = 0.85,
    chunk_id: uuid.UUID | None = None,
) -> RetrievedChunkResult:
    return RetrievedChunkResult(
        chunk_document_id=chunk_id or uuid.uuid4(),
        plant_knowledge_id=uuid.uuid4(),
        chunk_kind=kind,
        chunk_text=text,
        similarity_score=score,
        rank=1,
        rag_layer="care_knowledge",
    )


def _decision(route: str = "rag_lookup") -> QuestionRouteDecision:
    return QuestionRouteDecision.make(route=route, confidence=0.9, reason_codes=["test"])  # type: ignore[arg-type]


_svc = RagFastPathAnswerService()

# ---------------------------------------------------------------------------
# check_sufficiency
# ---------------------------------------------------------------------------


def test_sufficient_with_care_requirement_chunk() -> None:
    assert check_sufficiency([_chunk("care_requirement")])


def test_sufficient_with_seasonal_watering_chunk() -> None:
    assert check_sufficiency([_chunk("seasonal_watering")])


def test_sufficient_with_placement_chunk() -> None:
    assert check_sufficiency([_chunk("placement")])


def test_sufficient_with_identity_chunk() -> None:
    assert check_sufficiency([_chunk("identity")])


def test_sufficient_with_visual_trait_chunk() -> None:
    assert check_sufficiency([_chunk("visual_trait")])


def test_sufficient_with_pest_reference_chunk() -> None:
    assert check_sufficiency([_chunk("pest_reference")])


def test_insufficient_when_no_chunks() -> None:
    assert not check_sufficiency([])


def test_insufficient_when_unknown_kind() -> None:
    assert not check_sufficiency([_chunk("unknown_kind")])


def test_fast_path_kinds_constant_covers_all_expected() -> None:
    expected = {"care_requirement", "seasonal_watering", "placement", "identity", "visual_trait", "pest_reference"}
    assert FAST_PATH_KINDS == expected


# ---------------------------------------------------------------------------
# chunks_to_answer — pure helper
# ---------------------------------------------------------------------------


def test_answer_contains_chunk_text_snippet() -> None:
    c = _chunk(text="이 식물은 물을 자주 주지 않아도 됩니다. 토양 표면이 건조할 때 물을 주세요.")
    a = chunks_to_answer([c], "물주기")
    assert "이 식물은 물을 자주 주지 않아도" in a.결론


def test_answer_근거_contains_chunk_kind() -> None:
    c = _chunk(kind="care_requirement")
    a = chunks_to_answer([c], "물주기")
    assert "care_requirement" in a.근거


def test_answer_근거_contains_similarity_score() -> None:
    c = _chunk(score=0.92)
    a = chunks_to_answer([c], "물주기")
    assert "0.92" in a.근거


def test_answer_행동_is_nonempty() -> None:
    a = chunks_to_answer([_chunk()], "물주기")
    assert a.행동.strip()


def test_answer_주의_is_nonempty() -> None:
    a = chunks_to_answer([_chunk()], "물주기")
    assert a.주의.strip()


def test_answer_multiple_chunks_cited_in_근거() -> None:
    chunks = [_chunk("care_requirement", score=0.9), _chunk("seasonal_watering", score=0.8)]
    a = chunks_to_answer(chunks, "물주기")
    assert "care_requirement" in a.근거
    assert "seasonal_watering" in a.근거


def test_answer_text_without_sentence_boundary() -> None:
    c = _chunk(text="짧은텍스트")
    a = chunks_to_answer([c], "물주기")
    assert "짧은텍스트" in a.결론
    assert a.행동  # fallback action


def test_answer_is_parsed_answer_instance() -> None:
    a = chunks_to_answer([_chunk()], "물주기")
    assert isinstance(a, ParsedAnswer)


# ---------------------------------------------------------------------------
# RagFastPathAnswerService.evaluate() — insufficient path
# ---------------------------------------------------------------------------


def test_evaluate_empty_chunks_returns_llm_required() -> None:
    result = _svc.evaluate("물주기", _decision(), [])
    assert result.second_llm_required
    assert not result.is_sufficient
    assert result.answer is None


def test_evaluate_unknown_kind_returns_llm_required() -> None:
    result = _svc.evaluate("물주기", _decision(), [_chunk("unknown_kind")])
    assert result.second_llm_required
    assert result.answer is None


# ---------------------------------------------------------------------------
# RagFastPathAnswerService.evaluate() — sufficient, non-pest path
# ---------------------------------------------------------------------------


def test_evaluate_care_requirement_is_sufficient() -> None:
    result = _svc.evaluate("물주기", _decision(), [_chunk("care_requirement")])
    assert result.is_sufficient
    assert not result.second_llm_required
    assert result.answer is not None


def test_evaluate_returns_rag_fast_path_result() -> None:
    result = _svc.evaluate("물주기", _decision(), [_chunk()])
    assert isinstance(result, RagFastPathResult)


def test_evaluate_non_pest_diagnosis_allowed_true() -> None:
    result = _svc.evaluate("배치", _decision(), [_chunk("placement")])
    assert result.diagnosis_allowed
    assert not result.is_reference_only


def test_evaluate_chunk_ids_populated() -> None:
    cid = uuid.uuid4()
    result = _svc.evaluate("물주기", _decision(), [_chunk(chunk_id=cid)])
    assert cid in result.chunk_ids_used


def test_evaluate_max_three_chunk_ids() -> None:
    chunks = [_chunk() for _ in range(5)]
    result = _svc.evaluate("물주기", _decision(), chunks)
    assert len(result.chunk_ids_used) <= 3


# ---------------------------------------------------------------------------
# RagFastPathAnswerService.evaluate() — pest_reference path
# ---------------------------------------------------------------------------


def test_evaluate_pest_reference_is_reference_only() -> None:
    result = _svc.evaluate("병충해", _decision("pest_reference"), [_chunk("pest_reference")])
    assert result.is_reference_only
    assert not result.diagnosis_allowed


def test_evaluate_pest_reference_disclaimer_in_주의() -> None:
    result = _svc.evaluate("병충해", _decision("pest_reference"), [_chunk("pest_reference")])
    assert result.answer is not None
    assert REQUIRED_DISCLAIMER in result.answer.주의


def test_evaluate_pest_reference_not_llm_required() -> None:
    result = _svc.evaluate("병충해", _decision("pest_reference"), [_chunk("pest_reference")])
    assert not result.second_llm_required


def test_evaluate_pest_reference_answer_not_none() -> None:
    result = _svc.evaluate("병충해", _decision("pest_reference"), [_chunk("pest_reference")])
    assert result.answer is not None


def test_evaluate_mixed_chunks_with_pest_applies_guardrail() -> None:
    chunks = [_chunk("pest_reference"), _chunk("care_requirement")]
    result = _svc.evaluate("병충해", _decision(), chunks)
    assert result.is_reference_only
    assert REQUIRED_DISCLAIMER in result.answer.주의


# ---------------------------------------------------------------------------
# No LLM import guard
# ---------------------------------------------------------------------------


def test_service_does_not_import_llm() -> None:
    from pathlib import Path
    src = Path("app/services/rag_fast_path_answer_service.py").read_text(encoding="utf-8")
    for forbidden in ("openai", "anthropic", "QwenLLM", "vllm"):
        assert forbidden not in src, f"LLM reference found: {forbidden!r}"
