"""POST /retrieval/query — TICKET-014C / TICKET-048."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.db.session import AsyncSessionLocal
from app.domain.rag import IncompatibleEmbeddingError
from app.domain.retrieval import RAG_LAYER_TO_CHUNK_KINDS
from app.schemas.retrieval import ChunkResultItem, RetrievalRequest, RetrievalResponse
from app.services.retrieval_service import RetrievalService

router = APIRouter(prefix="/retrieval", tags=["retrieval"])

_PEST_KINDS = frozenset(RAG_LAYER_TO_CHUNK_KINDS.get("pest_disease_reference", ()))


@router.post("/query", response_model=RetrievalResponse, summary="Hybrid knowledge retrieval")
async def query_retrieval(body: RetrievalRequest) -> RetrievalResponse | JSONResponse:
    """Run hybrid retrieval over plant knowledge chunks.

    Results are ranked by semantic similarity (dot product of L2-normalised
    Qwen embeddings). The run is persisted for audit and is idempotent on
    `request_id`. Returns 503 when no stored embeddings are compatible with
    the current Qwen model/dim contract.
    """
    try:
        async with AsyncSessionLocal() as session:
            svc = RetrievalService(session)
            run = await svc.query(body)
            await session.commit()
    except IncompatibleEmbeddingError as exc:
        return JSONResponse(
            status_code=503,
            content={"detail": str(exc), "error": "incompatible_embedding"},
        )

    return RetrievalResponse(
        request_id=run.request_id,
        question=run.question,
        total_results=len(run.results),
        from_cache=run.from_cache,
        results=[
            ChunkResultItem(
                rank=r.rank,
                chunk_document_id=r.chunk_document_id,
                plant_knowledge_id=r.plant_knowledge_id,
                chunk_kind=r.chunk_kind,
                chunk_text=r.chunk_text,
                similarity_score=r.similarity_score,
                layer=r.rag_layer,
                source_metadata=None,
                structured_metadata={
                    "reference_only": r.chunk_kind in _PEST_KINDS,
                },
            )
            for r in run.results
        ],
    )
