"""TICKET-014C — retrieval domain, schema, and service tests (no DB, no model)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.retrieval import (
    ALL_RAG_LAYERS,
    RAG_LAYER_TO_CHUNK_KINDS,
    RetrievalFilter,
    RetrievedChunkResult,
)
from app.schemas.retrieval import RetrievalRequest

# ---------------------------------------------------------------------------
# Domain constants
# ---------------------------------------------------------------------------


def test_all_rag_layers_has_three_entries() -> None:
    assert len(ALL_RAG_LAYERS) == 3


def test_rag_layer_to_chunk_kinds_covers_all_chunk_kinds() -> None:
    from app.domain.chunk import CHUNK_KINDS

    covered: set[str] = set()
    for kinds in RAG_LAYER_TO_CHUNK_KINDS.values():
        covered.update(kinds)
    assert covered == set(CHUNK_KINDS)


def test_species_profile_layer_maps_to_identity_visual_placement() -> None:
    kinds = set(RAG_LAYER_TO_CHUNK_KINDS["species_profile"])
    assert "identity" in kinds
    assert "visual_trait" in kinds
    assert "placement" in kinds


def test_care_knowledge_layer_maps_to_care_and_watering() -> None:
    kinds = set(RAG_LAYER_TO_CHUNK_KINDS["care_knowledge"])
    assert "care_requirement" in kinds
    assert "seasonal_watering" in kinds


def test_pest_disease_reference_maps_to_pest_reference() -> None:
    assert RAG_LAYER_TO_CHUNK_KINDS["pest_disease_reference"] == ("pest_reference",)


# ---------------------------------------------------------------------------
# RetrievalRequest schema
# ---------------------------------------------------------------------------


def test_retrieval_request_defaults() -> None:
    req = RetrievalRequest(
        request_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        question="몬스테라 물주기",
    )
    assert req.top_k == 5
    assert req.species_profile_id is None
    assert set(req.rag_layers) == set(ALL_RAG_LAYERS)


def test_retrieval_request_rejects_empty_question() -> None:
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        RetrievalRequest(
            request_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            question="",
        )


def test_retrieval_request_rejects_top_k_zero() -> None:
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        RetrievalRequest(
            request_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            question="test",
            top_k=0,
        )


def test_retrieval_request_rejects_top_k_over_20() -> None:
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        RetrievalRequest(
            request_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            question="test",
            top_k=21,
        )


def test_retrieval_request_forbids_extra_fields() -> None:
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        RetrievalRequest(
            request_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            question="test",
            unknown_field="bad",
        )


# ---------------------------------------------------------------------------
# HybridRetriever: _dot helper
# ---------------------------------------------------------------------------


def test_dot_product_orthogonal_vectors() -> None:
    from app.retrieval.hybrid_retriever import _dot

    assert _dot([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_dot_product_parallel_unit_vectors() -> None:
    from app.retrieval.hybrid_retriever import _dot

    assert _dot([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)


def test_dot_product_general() -> None:
    from app.retrieval.hybrid_retriever import _dot

    assert _dot([0.5, 0.5], [0.5, 0.5]) == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# HybridRetriever.retrieve: empty DB returns empty list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retrieve_returns_empty_when_no_docs() -> None:
    from app.retrieval.hybrid_retriever import HybridRetriever

    session = AsyncMock()
    session.execute = AsyncMock(
        return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))
    )
    emb = MagicMock()
    emb.embed = MagicMock(return_value=[0.1] * 4)

    retriever = HybridRetriever(session, emb)
    filt = RetrievalFilter(
        question="test",
        species_profile_id=None,
        rag_layers=("care_knowledge",),
        top_k=5,
    )
    results = await retriever.retrieve(filt)
    assert results == []


# ---------------------------------------------------------------------------
# HybridRetriever.retrieve: returns top_k ranked results
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retrieve_ranks_by_similarity() -> None:
    from app.models.plant_chunk_document import PlantChunkDocument
    from app.models.plant_chunk_embedding import PlantChunkEmbedding
    from app.retrieval.hybrid_retriever import HybridRetriever

    doc_id_a = uuid.uuid4()
    doc_id_b = uuid.uuid4()
    kid = uuid.uuid4()

    doc_a = MagicMock(spec=PlantChunkDocument)
    doc_a.id = doc_id_a
    doc_a.plant_knowledge_id = kid
    doc_a.chunk_kind = "care_requirement"
    doc_a.chunk_text = "A text"

    doc_b = MagicMock(spec=PlantChunkDocument)
    doc_b.id = doc_id_b
    doc_b.plant_knowledge_id = kid
    doc_b.chunk_kind = "seasonal_watering"
    doc_b.chunk_text = "B text"

    emb_a = MagicMock(spec=PlantChunkEmbedding)
    emb_a.chunk_document_id = doc_id_a
    emb_a.vector = [1.0, 0.0]

    emb_b = MagicMock(spec=PlantChunkEmbedding)
    emb_b.chunk_document_id = doc_id_b
    emb_b.vector = [0.0, 1.0]

    # query vector points toward doc_a
    query_vec = [0.9, 0.1]

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
    emb_svc.embed = MagicMock(return_value=query_vec)

    retriever = HybridRetriever(session, emb_svc)
    filt = RetrievalFilter(
        question="물주기",
        species_profile_id=None,
        rag_layers=("care_knowledge",),
        top_k=2,
    )
    results = await retriever.retrieve(filt)

    assert len(results) == 2
    assert results[0].rank == 1
    assert results[0].chunk_document_id == doc_id_a
    assert results[0].similarity_score > results[1].similarity_score


# ---------------------------------------------------------------------------
# RetrievalService: idempotency (cached path)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retrieval_service_returns_cached_on_duplicate_request_id() -> None:
    from app.models.retrieval_result_chunk import RetrievalResultChunk
    from app.models.retrieval_run import RetrievalRun
    from app.services.retrieval_service import RetrievalService

    run_id = uuid.uuid4()
    cached_run = MagicMock(spec=RetrievalRun)
    cached_run.id = run_id
    cached_run.question = "몬스테라 물주기"

    cached_chunk = MagicMock(spec=RetrievalResultChunk)
    cached_chunk.chunk_document_id = uuid.uuid4()
    cached_chunk.plant_knowledge_id = uuid.uuid4()
    cached_chunk.chunk_kind = "care_requirement"
    cached_chunk.chunk_text = "몬스테라 관리 방법."
    cached_chunk.similarity_score = 0.9
    cached_chunk.rank = 1

    session = AsyncMock()
    session.get = AsyncMock(return_value=cached_run)
    session.execute = AsyncMock(
        return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[cached_chunk]))))
    )

    svc = RetrievalService(session)
    req = RetrievalRequest(
        request_id=run_id,
        user_id=uuid.uuid4(),
        question="몬스테라 물주기",
    )
    result = await svc.query(req)

    assert result.from_cache is True
    assert result.request_id == run_id
    assert len(result.results) == 1


# ---------------------------------------------------------------------------
# RetrievalService: fresh query (insert path)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retrieval_service_fresh_query_calls_retriever() -> None:
    from app.services.retrieval_service import RetrievalService

    req_id = uuid.uuid4()
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)  # no cache
    session.add = MagicMock()
    session.flush = AsyncMock()

    fake_result = RetrievedChunkResult(
        chunk_document_id=uuid.uuid4(),
        plant_knowledge_id=uuid.uuid4(),
        chunk_kind="identity",
        chunk_text="몬스테라 식물입니다.",
        similarity_score=0.85,
        rank=1,
    )

    svc = RetrievalService(session)

    with (
        patch("app.services.retrieval_service._get_embedding_service") as mock_emb_factory,
        patch("app.services.retrieval_service.HybridRetriever") as mock_retriever_cls,
    ):
        mock_emb = MagicMock()
        mock_emb.model_name = "test-model"
        mock_emb_factory.return_value = mock_emb

        mock_retriever = AsyncMock()
        mock_retriever.retrieve = AsyncMock(return_value=[fake_result])
        mock_retriever_cls.return_value = mock_retriever

        req = RetrievalRequest(
            request_id=req_id,
            user_id=uuid.uuid4(),
            question="몬스테라 물주기",
        )
        result = await svc.query(req)

    assert result.from_cache is False
    assert result.request_id == req_id
    assert len(result.results) == 1
    assert result.results[0].chunk_kind == "identity"
    assert session.add.call_count == 2  # RetrievalRun + 1 RetrievalResultChunk


# ---------------------------------------------------------------------------
# No forbidden imports
# ---------------------------------------------------------------------------


def test_hybrid_retriever_has_no_llm_imports() -> None:
    import app.retrieval.hybrid_retriever as mod

    src = open(mod.__file__, encoding="utf-8").read()
    for forbidden in ("openai", "anthropic", "torch", "prompt", "answer"):
        assert forbidden not in src, f"Forbidden: {forbidden!r}"


def test_retrieval_service_has_no_llm_imports() -> None:
    import app.services.retrieval_service as mod

    src = open(mod.__file__, encoding="utf-8").read()
    for forbidden in ("openai", "anthropic", "torch", "PromptBuilder", "EvidenceBuilder"):
        assert forbidden not in src, f"Forbidden: {forbidden!r}"


# ---------------------------------------------------------------------------
# Migration file
# ---------------------------------------------------------------------------


def test_migration_0005_exists() -> None:
    from pathlib import Path

    m = Path("alembic/versions/0005_ticket14c_retrieval_tables.py")
    assert m.exists()


def test_migration_0005_has_both_tables() -> None:
    from pathlib import Path

    src = Path("alembic/versions/0005_ticket14c_retrieval_tables.py").read_text(encoding="utf-8")
    assert "retrieval_runs" in src
    assert "retrieval_result_chunks" in src
    assert "def upgrade" in src
    assert "def downgrade" in src
