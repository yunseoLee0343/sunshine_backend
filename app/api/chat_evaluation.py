"""Chat evaluation API — TICKET-034.

Ground truth CRUD:
  POST   /evaluation/ground-truth          — create entry
  GET    /evaluation/ground-truth          — list all entries
  DELETE /evaluation/ground-truth/{id}     — remove entry

Evaluation results:
  GET    /evaluation/results/{request_id}  — get evaluation for a chat run
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.chat_evaluation import ChatEvaluationResult, GroundTruthEntry

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


async def _get_session():
    async with AsyncSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# Request / Response schemas (local — no shared schema file needed)
# ---------------------------------------------------------------------------


class GroundTruthCreateRequest(BaseModel):
    question_keywords: list[str]
    expected_answer: str
    required_keywords: list[str]
    intent: str


class GroundTruthResponse(BaseModel):
    id: uuid.UUID
    question_keywords: list[str]
    expected_answer: str
    required_keywords: list[str]
    intent: str
    created_at: datetime


class EvaluationResultResponse(BaseModel):
    id: uuid.UUID
    request_id: uuid.UUID
    ab_test_group: str
    faithfulness: float
    answer_relevance: float
    ground_truth_similarity: float
    matched_ground_truth_id: uuid.UUID | None
    created_at: datetime


# ---------------------------------------------------------------------------
# Ground truth endpoints
# ---------------------------------------------------------------------------


@router.post("/ground-truth", response_model=GroundTruthResponse, status_code=201)
async def create_ground_truth(
    body: GroundTruthCreateRequest,
    session: AsyncSession = Depends(_get_session),
) -> GroundTruthResponse:
    entry = GroundTruthEntry(
        id=uuid.uuid4(),
        question_keywords=body.question_keywords,
        expected_answer=body.expected_answer,
        required_keywords=body.required_keywords,
        intent=body.intent,
        created_at=datetime.now(UTC),
    )
    session.add(entry)
    await session.commit()
    return GroundTruthResponse(
        id=entry.id,
        question_keywords=list(entry.question_keywords),
        expected_answer=entry.expected_answer,
        required_keywords=list(entry.required_keywords),
        intent=entry.intent,
        created_at=entry.created_at,
    )


@router.get("/ground-truth", response_model=list[GroundTruthResponse])
async def list_ground_truth(
    session: AsyncSession = Depends(_get_session),
) -> list[GroundTruthResponse]:
    result = await session.execute(
        select(GroundTruthEntry).order_by(GroundTruthEntry.created_at.desc())
    )
    entries = list(result.scalars().all())
    return [
        GroundTruthResponse(
            id=e.id,
            question_keywords=list(e.question_keywords),
            expected_answer=e.expected_answer,
            required_keywords=list(e.required_keywords),
            intent=e.intent,
            created_at=e.created_at,
        )
        for e in entries
    ]


@router.delete("/ground-truth/{entry_id}", status_code=204)
async def delete_ground_truth(
    entry_id: uuid.UUID,
    session: AsyncSession = Depends(_get_session),
) -> None:
    entry = await session.get(GroundTruthEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="ground truth entry not found")
    await session.delete(entry)
    await session.commit()


# ---------------------------------------------------------------------------
# Evaluation result endpoint
# ---------------------------------------------------------------------------


@router.get("/results/{request_id}", response_model=EvaluationResultResponse)
async def get_evaluation_result(
    request_id: uuid.UUID,
    session: AsyncSession = Depends(_get_session),
) -> EvaluationResultResponse:
    result = await session.execute(
        select(ChatEvaluationResult)
        .where(ChatEvaluationResult.request_id == request_id)
        .order_by(ChatEvaluationResult.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="evaluation result not found")
    return EvaluationResultResponse(
        id=row.id,
        request_id=row.request_id,
        ab_test_group=row.ab_test_group,
        faithfulness=row.faithfulness,
        answer_relevance=row.answer_relevance,
        ground_truth_similarity=row.ground_truth_similarity,
        matched_ground_truth_id=row.matched_ground_truth_id,
        created_at=row.created_at,
    )
