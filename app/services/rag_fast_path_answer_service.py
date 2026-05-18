"""RagFastPathAnswerService — TICKET-064.

Answers simple RAG-lookup questions from retrieved chunks without an LLM call
when retrieved evidence is sufficient.

Sufficiency rule:
  - at least 1 chunk
  - top chunk_kind is in FAST_PATH_KINDS
  - pest_reference chunks are answered with reference-only guardrail applied

No async — chunks are passed in already fetched. Pure, deterministic, testable.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.domain.question_router import QuestionRouteDecision
from app.domain.retrieval import RetrievedChunkResult
from app.schemas.chat_answer import ParsedAnswer
from app.services.pest_reference_guardrail import PestReferenceGuardrail

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FAST_PATH_KINDS: frozenset[str] = frozenset(
    [
        "care_requirement",
        "seasonal_watering",
        "placement",
        "identity",
        "visual_trait",
        "pest_reference",
    ]
)

# Max chars taken from a single chunk for the answer sections.
_CONCLUSION_LIMIT = 200
_ACTION_LIMIT = 200
_MAX_CHUNKS_USED = 3

_GENERIC_CAUTION = "식물 종류와 환경/계절에 따라 조정이 필요할 수 있어요."

# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class RagFastPathResult:
    """Outcome of the RAG fast path evaluation."""

    answer: ParsedAnswer | None
    second_llm_required: bool
    is_sufficient: bool
    chunk_ids_used: list[uuid.UUID] = field(default_factory=list)
    is_reference_only: bool = False
    diagnosis_allowed: bool = True


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _split_text(text: str) -> tuple[str, str]:
    """Split chunk text into (conclusion, action) by first sentence boundary.

    Returns two non-empty strings; if the text has no clear split the full
    text is used for conclusion and a generic fallback for action.
    """
    text = text.strip()
    for sep in ("다. ", "요. ", "니다. ", "어요. ", "세요. "):
        idx = text.find(sep)
        if 0 < idx < len(text) - len(sep):
            conclusion = text[: idx + len(sep) - 1].strip()
            action = text[idx + len(sep) :].strip()
            return conclusion[:_CONCLUSION_LIMIT], action[:_ACTION_LIMIT]

    # No sentence boundary found — use first _CONCLUSION_LIMIT chars
    return text[:_CONCLUSION_LIMIT], ""


def check_sufficiency(chunks: list[RetrievedChunkResult]) -> bool:
    """Return True when the chunk list meets the fast-path sufficiency rule."""
    if not chunks:
        return False
    return chunks[0].chunk_kind in FAST_PATH_KINDS


def chunks_to_answer(
    chunks: list[RetrievedChunkResult],
    question: str,
) -> ParsedAnswer:
    """Build a ParsedAnswer from the top retrieved chunks. No LLM."""
    top_chunks = chunks[:_MAX_CHUNKS_USED]
    top = top_chunks[0]

    conclusion, action_from_text = _split_text(top.chunk_text)

    # 결론 — lead with the retrieved knowledge
    결론 = f"검색된 식물 관리 지식 기준: {conclusion}"

    # 근거 — cite chunk kinds and similarity scores
    cite_parts = [
        f"chunk_kind={c.chunk_kind}, 유사도={c.similarity_score:.2f}"
        for c in top_chunks
    ]
    근거 = "사용한 근거: " + " | ".join(cite_parts)

    # 행동 — second part of text or fallback
    행동 = action_from_text if action_from_text else "위 내용을 참고하여 관리해 주세요."

    return ParsedAnswer(결론=결론, 근거=근거, 행동=행동, 주의=_GENERIC_CAUTION)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

_guardrail = PestReferenceGuardrail()


class RagFastPathAnswerService:
    """Evaluates whether retrieved RAG chunks are sufficient to answer without LLM.

    evaluate() is synchronous — no DB, no network.
    """

    def evaluate(
        self,
        question: str,
        decision: QuestionRouteDecision,
        chunks: list[RetrievedChunkResult],
    ) -> RagFastPathResult:
        """Return a RagFastPathResult.

        If chunks are insufficient, answer=None and second_llm_required=True.
        If pest_reference chunks are used, PestReferenceGuardrail is applied.
        """
        if not check_sufficiency(chunks):
            return RagFastPathResult(
                answer=None,
                second_llm_required=True,
                is_sufficient=False,
            )

        top_chunks = chunks[:_MAX_CHUNKS_USED]
        chunk_ids = [c.chunk_document_id for c in top_chunks]

        answer = chunks_to_answer(top_chunks, question)

        is_pest = any(c.chunk_kind == "pest_reference" for c in top_chunks)
        if is_pest:
            guardrail_result = _guardrail.apply(answer)
            return RagFastPathResult(
                answer=guardrail_result.answer,
                second_llm_required=False,
                is_sufficient=True,
                chunk_ids_used=chunk_ids,
                is_reference_only=True,
                diagnosis_allowed=False,
            )

        return RagFastPathResult(
            answer=answer,
            second_llm_required=False,
            is_sufficient=True,
            chunk_ids_used=chunk_ids,
            is_reference_only=False,
            diagnosis_allowed=True,
        )
