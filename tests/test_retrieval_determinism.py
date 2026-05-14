"""TICKET-048 — HybridRetriever deterministic sort tests."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.retrieval import RetrievalFilter
from app.models.plant_chunk_document import PlantChunkDocument
from app.models.plant_chunk_embedding import PlantChunkEmbedding
from app.retrieval.hybrid_retriever import HybridRetriever


def _make_doc(chunk_kind: str = "care_requirement") -> MagicMock:
    doc = MagicMock(spec=PlantChunkDocument)
    doc.id = uuid.uuid4()
    doc.plant_knowledge_id = uuid.uuid4()
    doc.chunk_kind = chunk_kind
    doc.chunk_text = "text"
    return doc


def _make_emb(doc_id: uuid.UUID, vector: list[float]) -> MagicMock:
    row = MagicMock(spec=PlantChunkEmbedding)
    row.chunk_document_id = doc_id
    row.model_name = "Qwen/Qwen3-Embedding-0.6B"
    row.vector_dim = 1024
    row.vector = vector
    return row


@pytest.mark.asyncio
async def test_tied_scores_sorted_by_chunk_id() -> None:
    doc_a = _make_doc()
    doc_b = _make_doc()
    # Force deterministic IDs so we can predict order
    doc_a.id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    doc_b.id = uuid.UUID("00000000-0000-0000-0000-000000000002")

    # Both get score 1.0 (parallel unit vectors)
    emb_a = _make_emb(doc_a.id, [1.0, 0.0])
    emb_b = _make_emb(doc_b.id, [1.0, 0.0])

    call_count = 0

    async def fake_execute(stmt):
        nonlocal call_count
        call_count += 1
        mock = MagicMock()
        if call_count == 1:
            mock.scalars.return_value.all.return_value = [doc_b, doc_a]  # purposely reversed
        else:
            mock.scalars.return_value.all.return_value = [emb_b, emb_a]
        return mock

    session = AsyncMock()
    session.execute = fake_execute

    emb_svc = MagicMock()
    emb_svc.embed = MagicMock(return_value=[1.0, 0.0])

    retriever = HybridRetriever(session, emb_svc)
    filt = RetrievalFilter(
        question="test",
        species_profile_id=None,
        rag_layers=("care_knowledge",),
        top_k=2,
    )
    results = await retriever.retrieve(filt)

    assert len(results) == 2
    # Tied scores: doc_a (smaller UUID string) should come first
    assert results[0].chunk_document_id == doc_a.id
    assert results[1].chunk_document_id == doc_b.id


@pytest.mark.asyncio
async def test_higher_score_always_ranked_first() -> None:
    doc_a = _make_doc()
    doc_b = _make_doc()
    emb_a = _make_emb(doc_a.id, [0.8, 0.6])
    emb_b = _make_emb(doc_b.id, [0.1, 0.0])

    call_count = 0

    async def fake_execute(stmt):
        nonlocal call_count
        call_count += 1
        mock = MagicMock()
        if call_count == 1:
            mock.scalars.return_value.all.return_value = [doc_a, doc_b]
        else:
            mock.scalars.return_value.all.return_value = [emb_a, emb_b]
        return mock

    session = AsyncMock()
    session.execute = fake_execute

    emb_svc = MagicMock()
    emb_svc.embed = MagicMock(return_value=[1.0, 0.0])

    retriever = HybridRetriever(session, emb_svc)
    filt = RetrievalFilter(
        question="test",
        species_profile_id=None,
        rag_layers=("care_knowledge",),
        top_k=2,
    )
    results = await retriever.retrieve(filt)

    assert results[0].similarity_score > results[1].similarity_score
    assert results[0].rank == 1
    assert results[1].rank == 2
