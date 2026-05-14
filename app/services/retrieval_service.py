"""RetrievalService — TICKET-014C / TICKET-048.

Orchestrates: idempotency check → hybrid retrieval → persist run + results.
No LLM, no answer generation.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.retrieval import RetrievalFilter, RetrievalRunResult, RetrievedChunkResult
from app.embedding.local_embedding_service import LocalEmbeddingService
from app.models.retrieval_result_chunk import RetrievalResultChunk
from app.models.retrieval_run import RetrievalRun
from app.retrieval.hybrid_retriever import HybridRetriever
from app.schemas.retrieval import RetrievalRequest

# Module-level lazy singleton — model is NOT loaded at import time.
_embedding_service: LocalEmbeddingService | None = None


def _get_embedding_service() -> LocalEmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = LocalEmbeddingService()
    return _embedding_service


class RetrievalService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def query(self, req: RetrievalRequest) -> RetrievalRunResult:
        # ---- idempotency ---------------------------------------------------
        cached = await self.session.get(RetrievalRun, req.request_id)
        if cached is not None:
            return await self._load_cached(cached)

        # ---- embed query ---------------------------------------------------
        emb = _get_embedding_service()
        query_vec = emb.embed(req.question)
        query_vector_hash = hashlib.sha256(
            json.dumps(query_vec, default=str).encode()
        ).hexdigest()

        # ---- retrieve ------------------------------------------------------
        retriever = HybridRetriever(
            self.session,
            emb,
            expected_model=emb.model_name,
            expected_dim=emb.embedding_dim,
        )
        filt = RetrievalFilter(
            question=req.question,
            species_profile_id=req.species_profile_id,
            rag_layers=tuple(req.rag_layers),
            top_k=req.top_k,
        )
        results = await retriever.retrieve(filt)

        # ---- persist -------------------------------------------------------
        now = datetime.now(UTC)
        run = RetrievalRun(
            id=req.request_id,
            user_id=req.user_id,
            plant_id=req.plant_id,
            question=req.question,
            question_hash=hashlib.sha256(req.question.encode()).hexdigest(),
            species_profile_id=req.species_profile_id,
            rag_layers=list(req.rag_layers),
            top_k=req.top_k,
            model_name=emb.model_name,
            embedding_model_rev=emb.model_rev,
            query_vector_hash=query_vector_hash,
            total_results=len(results),
            created_at=now,
        )
        self.session.add(run)
        await self.session.flush()

        for r in results:
            self.session.add(
                RetrievalResultChunk(
                    id=uuid.uuid4(),
                    run_id=req.request_id,
                    rank=r.rank,
                    chunk_document_id=r.chunk_document_id,
                    plant_knowledge_id=r.plant_knowledge_id,
                    chunk_kind=r.chunk_kind,
                    chunk_text=r.chunk_text,
                    similarity_score=r.similarity_score,
                    created_at=now,
                )
            )
        await self.session.flush()

        return RetrievalRunResult(
            request_id=req.request_id,
            question=req.question,
            results=results,
            from_cache=False,
        )

    async def _load_cached(self, run: RetrievalRun) -> RetrievalRunResult:
        result = await self.session.execute(
            select(RetrievalResultChunk)
            .where(RetrievalResultChunk.run_id == run.id)
            .order_by(RetrievalResultChunk.rank)
        )
        rows = result.scalars().all()
        results = [
            RetrievedChunkResult(
                chunk_document_id=r.chunk_document_id,
                plant_knowledge_id=r.plant_knowledge_id,
                chunk_kind=r.chunk_kind,
                chunk_text=r.chunk_text,
                similarity_score=r.similarity_score,
                rank=r.rank,
            )
            for r in rows
        ]
        return RetrievalRunResult(
            request_id=run.id,
            question=run.question,
            results=results,
            from_cache=True,
        )
