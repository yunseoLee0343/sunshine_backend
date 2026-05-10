"""POST /retrieval/query — TICKET-014C."""

from __future__ import annotations

from fastapi import APIRouter

from app.db.session import AsyncSessionLocal
from app.schemas.retrieval import RetrievalRequest, RetrievalResponse
from app.services.retrieval_service import RetrievalService

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


@router.post("/query", response_model=RetrievalResponse)
async def query_retrieval(body: RetrievalRequest) -> RetrievalResponse:
    async with AsyncSessionLocal() as session:
        svc = RetrievalService(session)
        run = await svc.query(body)
        await session.commit()
    return RetrievalResponse(
        request_id=run.request_id,
        question=run.question,
        total_results=len(run.results),
        from_cache=run.from_cache,
        results=[
            {
                "rank": r.rank,
                "chunk_document_id": r.chunk_document_id,
                "plant_knowledge_id": r.plant_knowledge_id,
                "chunk_kind": r.chunk_kind,
                "chunk_text": r.chunk_text,
                "similarity_score": r.similarity_score,
            }
            for r in run.results
        ],
    )
