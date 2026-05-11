"""ChatEvaluationService — TICKET-034.

A/B routing, metric computation, ground truth matching, and persistence.

Metrics (all 0.0–1.0, pure functions — no I/O):
  faithfulness          : fraction of rule codes + chunk kinds referenced in answer
  answer_relevance      : Jaccard-style overlap of question keywords in answer text
  ground_truth_similarity: fraction of required_keywords found in answer text

No external evaluation APIs.  All scoring is deterministic keyword overlap.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.evaluation import (
    AbTestGroup,
    EvaluationMetrics,
    EvaluationResult,
    GroundTruthSpec,
)
from app.domain.evidence import ChunkEvidence, ForwardContext
from app.models.chat_evaluation import ChatEvaluationResult, GroundTruthEntry
from app.schemas.chat_answer import ParsedAnswer


# ---------------------------------------------------------------------------
# A/B group assignment
# ---------------------------------------------------------------------------


def assign_ab_group(request_id: uuid.UUID) -> AbTestGroup:
    """Deterministic: last byte of request_id → 'control' or 'experiment'."""
    return "control" if int(request_id.bytes[-1]) % 2 == 0 else "experiment"


# ---------------------------------------------------------------------------
# Metric helpers (pure functions)
# ---------------------------------------------------------------------------


def _answer_text(answer: ParsedAnswer) -> str:
    return " ".join([answer.결론, answer.근거, answer.행동, answer.주의])


def _extract_words(text: str) -> list[str]:
    """Return unique meaningful tokens (≥2 chars, Korean or Latin)."""
    return list({w for w in re.findall(r"[가-힣a-zA-Z]+", text.lower()) if len(w) >= 2})


def _chunk_mentioned(chunk: ChunkEvidence, answer_text_lower: str) -> bool:
    """True if the chunk's kind or any of its first few content words appear in the answer."""
    if chunk.chunk_kind.lower() in answer_text_lower:
        return True
    content_words = [w for w in re.findall(r"[가-힣a-zA-Z]+", chunk.chunk_text.lower()) if len(w) >= 2]
    return any(w in answer_text_lower for w in content_words[:5])


def compute_faithfulness(answer: ParsedAnswer, ctx: ForwardContext) -> float:
    """Fraction of evidence (rule codes + retrieved chunks) referenced in the answer.

    Returns 1.0 when there is no evidence to check (nothing to be unfaithful to).
    """
    answer_lower = _answer_text(answer).lower()
    code_total = len(ctx.rule_reason_codes)
    chunk_total = len(ctx.retrieved_chunks)

    if code_total == 0 and chunk_total == 0:
        return 1.0

    score = 0.0
    weight = 0.0

    if code_total > 0:
        hits = sum(1 for code in ctx.rule_reason_codes if code.lower() in answer_lower)
        score += (hits / code_total) * 0.5
        weight += 0.5

    if chunk_total > 0:
        hits = sum(1 for chunk in ctx.retrieved_chunks if _chunk_mentioned(chunk, answer_lower))
        score += (hits / chunk_total) * 0.5
        weight += 0.5

    return score / weight if weight > 0 else 1.0


def compute_answer_relevance(question: str, answer: ParsedAnswer) -> float:
    """Fraction of question keywords that appear in the combined answer text."""
    q_words = _extract_words(question)
    if not q_words:
        return 0.0
    answer_lower = _answer_text(answer).lower()
    hits = sum(1 for w in q_words if w in answer_lower)
    return hits / len(q_words)


def compute_ground_truth_similarity(
    answer: ParsedAnswer, spec: GroundTruthSpec | None
) -> float:
    """Fraction of the ground truth's required_keywords found in the answer."""
    if spec is None or not spec.required_keywords:
        return 0.0
    answer_lower = _answer_text(answer).lower()
    hits = sum(1 for kw in spec.required_keywords if kw.lower() in answer_lower)
    return hits / len(spec.required_keywords)


# ---------------------------------------------------------------------------
# Ground truth matching (DB-backed)
# ---------------------------------------------------------------------------


def _keyword_overlap(question: str, keywords: list[str]) -> int:
    """Count how many question_keywords appear in the question text."""
    question_lower = question.lower()
    return sum(1 for kw in keywords if kw.lower() in question_lower)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ChatEvaluationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_matching_ground_truth(
        self, question: str, intent: str
    ) -> GroundTruthSpec | None:
        """Return the GroundTruthEntry whose question_keywords best overlap with question.

        Filters by intent first; returns None when no entries exist for that intent.
        """
        result = await self.session.execute(
            select(GroundTruthEntry).where(GroundTruthEntry.intent == intent)
        )
        entries: list[GroundTruthEntry] = list(result.scalars().all())
        if not entries:
            return None

        best = max(
            entries,
            key=lambda e: _keyword_overlap(question, list(e.question_keywords or [])),
        )
        return GroundTruthSpec(
            id=best.id,
            question_keywords=list(best.question_keywords or []),
            expected_answer=best.expected_answer,
            required_keywords=list(best.required_keywords or []),
            intent=best.intent,
        )

    async def evaluate_and_save(
        self,
        *,
        request_id: uuid.UUID,
        question: str,
        answer: ParsedAnswer,
        ctx: ForwardContext,
        intent: str,
    ) -> EvaluationResult:
        """Compute all metrics, persist ChatEvaluationResult, return domain object."""
        group = assign_ab_group(request_id)
        spec = await self.find_matching_ground_truth(question, intent)

        metrics = EvaluationMetrics(
            faithfulness=compute_faithfulness(answer, ctx),
            answer_relevance=compute_answer_relevance(question, answer),
            ground_truth_similarity=compute_ground_truth_similarity(answer, spec),
        )

        row = ChatEvaluationResult(
            id=uuid.uuid4(),
            request_id=request_id,
            ab_test_group=group,
            faithfulness=metrics.faithfulness,
            answer_relevance=metrics.answer_relevance,
            ground_truth_similarity=metrics.ground_truth_similarity,
            matched_ground_truth_id=spec.id if spec else None,
            created_at=datetime.now(UTC),
        )
        self.session.add(row)
        await self.session.flush()

        return EvaluationResult(
            request_id=request_id,
            ab_test_group=group,
            metrics=metrics,
            matched_ground_truth_id=spec.id if spec else None,
        )
