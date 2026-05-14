"""TICKET-048 — HybridRetriever embedding compatibility tests."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.rag import IncompatibleEmbeddingError
from app.domain.retrieval import RetrievalFilter
from app.models.plant_chunk_document import PlantChunkDocument
from app.models.plant_chunk_embedding import PlantChunkEmbedding
from app.retrieval.hybrid_retriever import HybridRetriever, _is_compatible

# ---------------------------------------------------------------------------
# _is_compatible helper
# ---------------------------------------------------------------------------


def _mock_emb_row(model_name: str, vector_dim: int) -> MagicMock:
    row = MagicMock(spec=PlantChunkEmbedding)
    row.model_name = model_name
    row.vector_dim = vector_dim
    return row


def test_compatible_when_no_expected_values() -> None:
    row = _mock_emb_row("any-model", 512)
    assert _is_compatible(row, None, None) is True


def test_compatible_matching_model_and_dim() -> None:
    row = _mock_emb_row("Qwen/Qwen3-Embedding-0.6B", 1024)
    assert _is_compatible(row, "Qwen/Qwen3-Embedding-0.6B", 1024) is True


def test_incompatible_wrong_model() -> None:
    row = _mock_emb_row("old-model", 1024)
    assert _is_compatible(row, "Qwen/Qwen3-Embedding-0.6B", 1024) is False


def test_incompatible_wrong_dim() -> None:
    row = _mock_emb_row("Qwen/Qwen3-Embedding-0.6B", 384)
    assert _is_compatible(row, "Qwen/Qwen3-Embedding-0.6B", 1024) is False


def test_non_str_model_name_let_through() -> None:
    row = MagicMock(spec=PlantChunkEmbedding)
    # MagicMock attribute is not a str — should be let through (test-mock guard)
    assert _is_compatible(row, "Qwen/Qwen3-Embedding-0.6B", None) is True


def test_non_int_vector_dim_let_through() -> None:
    row = MagicMock(spec=PlantChunkEmbedding)
    row.model_name = "Qwen/Qwen3-Embedding-0.6B"
    assert _is_compatible(row, "Qwen/Qwen3-Embedding-0.6B", 1024) is True


# ---------------------------------------------------------------------------
# HybridRetriever.retrieve: IncompatibleEmbeddingError when all filtered
# ---------------------------------------------------------------------------


def _make_doc(chunk_kind: str = "care_requirement") -> MagicMock:
    doc = MagicMock(spec=PlantChunkDocument)
    doc.id = uuid.uuid4()
    doc.plant_knowledge_id = uuid.uuid4()
    doc.chunk_kind = chunk_kind
    doc.chunk_text = "sample text"
    return doc


def _make_emb_row(doc_id: uuid.UUID, model: str = "old-model", dim: int = 384) -> MagicMock:
    row = MagicMock(spec=PlantChunkEmbedding)
    row.chunk_document_id = doc_id
    row.model_name = model
    row.vector_dim = dim
    row.vector = [0.5, 0.5]
    return row


@pytest.mark.asyncio
async def test_incompatible_embedding_raises_503_error() -> None:
    doc = _make_doc()
    emb_row = _make_emb_row(doc.id, model="old-model", dim=384)

    call_count = 0

    async def fake_execute(stmt):
        nonlocal call_count
        call_count += 1
        mock = MagicMock()
        if call_count == 1:
            mock.scalars.return_value.all.return_value = [doc]
        else:
            mock.scalars.return_value.all.return_value = [emb_row]
        return mock

    session = AsyncMock()
    session.execute = fake_execute

    emb_svc = MagicMock()
    emb_svc.embed = MagicMock(return_value=[0.1] * 2)

    retriever = HybridRetriever(
        session,
        emb_svc,
        expected_model="Qwen/Qwen3-Embedding-0.6B",
        expected_dim=1024,
    )
    filt = RetrievalFilter(
        question="test",
        species_profile_id=None,
        rag_layers=("care_knowledge",),
        top_k=5,
    )
    with pytest.raises(IncompatibleEmbeddingError):
        await retriever.retrieve(filt)


@pytest.mark.asyncio
async def test_compatible_embedding_not_filtered() -> None:
    doc = _make_doc()
    emb_row = _make_emb_row(doc.id, model="Qwen/Qwen3-Embedding-0.6B", dim=1024)
    emb_row.vector = [1.0, 0.0]

    call_count = 0

    async def fake_execute(stmt):
        nonlocal call_count
        call_count += 1
        mock = MagicMock()
        if call_count == 1:
            mock.scalars.return_value.all.return_value = [doc]
        else:
            mock.scalars.return_value.all.return_value = [emb_row]
        return mock

    session = AsyncMock()
    session.execute = fake_execute

    emb_svc = MagicMock()
    emb_svc.embed = MagicMock(return_value=[1.0, 0.0])

    retriever = HybridRetriever(
        session,
        emb_svc,
        expected_model="Qwen/Qwen3-Embedding-0.6B",
        expected_dim=1024,
    )
    filt = RetrievalFilter(
        question="test",
        species_profile_id=None,
        rag_layers=("care_knowledge",),
        top_k=5,
    )
    results = await retriever.retrieve(filt)
    assert len(results) == 1


@pytest.mark.asyncio
async def test_empty_embedding_store_returns_empty_not_raises() -> None:
    doc = _make_doc()

    call_count = 0

    async def fake_execute(stmt):
        nonlocal call_count
        call_count += 1
        mock = MagicMock()
        if call_count == 1:
            mock.scalars.return_value.all.return_value = [doc]
        else:
            mock.scalars.return_value.all.return_value = []  # no embeddings at all
        return mock

    session = AsyncMock()
    session.execute = fake_execute

    emb_svc = MagicMock()
    emb_svc.embed = MagicMock(return_value=[0.1] * 2)

    retriever = HybridRetriever(
        session,
        emb_svc,
        expected_model="Qwen/Qwen3-Embedding-0.6B",
        expected_dim=1024,
    )
    filt = RetrievalFilter(
        question="test",
        species_profile_id=None,
        rag_layers=("care_knowledge",),
        top_k=5,
    )
    # all_embeddings is empty so IncompatibleEmbeddingError is NOT raised
    results = await retriever.retrieve(filt)
    assert results == []


# ---------------------------------------------------------------------------
# rag_layer field on results
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_result_includes_rag_layer() -> None:
    doc = _make_doc(chunk_kind="seasonal_watering")
    emb_row = _make_emb_row(doc.id, model="Qwen/Qwen3-Embedding-0.6B", dim=1024)
    emb_row.vector = [1.0, 0.0]

    call_count = 0

    async def fake_execute(stmt):
        nonlocal call_count
        call_count += 1
        mock = MagicMock()
        if call_count == 1:
            mock.scalars.return_value.all.return_value = [doc]
        else:
            mock.scalars.return_value.all.return_value = [emb_row]
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
        top_k=5,
    )
    results = await retriever.retrieve(filt)
    assert results[0].rag_layer == "care_knowledge"
