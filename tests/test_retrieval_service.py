"""TICKET-048 — RetrievalService: Qwen embedding metadata persistence tests."""

from __future__ import annotations

import hashlib
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.retrieval import RetrievedChunkResult
from app.schemas.retrieval import RetrievalRequest


def _make_req(**kwargs) -> RetrievalRequest:
    defaults = {
        "request_id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "question": "몬스테라 여름 물주기",
    }
    return RetrievalRequest(**{**defaults, **kwargs})


def _make_fake_result() -> RetrievedChunkResult:
    return RetrievedChunkResult(
        chunk_document_id=uuid.uuid4(),
        plant_knowledge_id=uuid.uuid4(),
        chunk_kind="seasonal_watering",
        chunk_text="여름엔 물을 자주 주세요.",
        similarity_score=0.87,
        rank=1,
        rag_layer="care_knowledge",
    )


@pytest.mark.asyncio
async def test_service_calls_embed_on_fresh_query() -> None:
    from app.services.retrieval_service import RetrievalService

    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.add = MagicMock()
    session.flush = AsyncMock()

    svc = RetrievalService(session)

    with (
        patch("app.services.retrieval_service._get_embedding_service") as mock_factory,
        patch("app.services.retrieval_service.HybridRetriever") as mock_cls,
    ):
        mock_emb = MagicMock()
        mock_emb.model_name = "Qwen/Qwen3-Embedding-0.6B"
        mock_emb.model_rev = "main"
        mock_emb.embedding_dim = 1024
        mock_emb.embed = MagicMock(return_value=[0.1] * 1024)
        mock_factory.return_value = mock_emb

        mock_retriever = AsyncMock()
        mock_retriever.retrieve = AsyncMock(return_value=[_make_fake_result()])
        mock_cls.return_value = mock_retriever

        req = _make_req()
        await svc.query(req)

    mock_emb.embed.assert_called_once_with(req.question)


@pytest.mark.asyncio
async def test_service_stores_qwen_model_name_in_run() -> None:
    from app.models.retrieval_run import RetrievalRun
    from app.services.retrieval_service import RetrievalService

    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    added_objects = []
    session.add = MagicMock(side_effect=added_objects.append)
    session.flush = AsyncMock()

    svc = RetrievalService(session)

    with (
        patch("app.services.retrieval_service._get_embedding_service") as mock_factory,
        patch("app.services.retrieval_service.HybridRetriever") as mock_cls,
    ):
        mock_emb = MagicMock()
        mock_emb.model_name = "Qwen/Qwen3-Embedding-0.6B"
        mock_emb.model_rev = "main"
        mock_emb.embedding_dim = 1024
        mock_emb.embed = MagicMock(return_value=[0.1] * 1024)
        mock_factory.return_value = mock_emb

        mock_retriever = AsyncMock()
        mock_retriever.retrieve = AsyncMock(return_value=[])
        mock_cls.return_value = mock_retriever

        await svc.query(_make_req())

    runs = [o for o in added_objects if isinstance(o, RetrievalRun)]
    assert len(runs) == 1
    assert runs[0].model_name == "Qwen/Qwen3-Embedding-0.6B"
    assert runs[0].embedding_model_rev == "main"


@pytest.mark.asyncio
async def test_service_stores_query_vector_hash() -> None:
    from app.models.retrieval_run import RetrievalRun
    from app.services.retrieval_service import RetrievalService

    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    added_objects = []
    session.add = MagicMock(side_effect=added_objects.append)
    session.flush = AsyncMock()

    query_vec = [0.5] * 1024

    svc = RetrievalService(session)

    with (
        patch("app.services.retrieval_service._get_embedding_service") as mock_factory,
        patch("app.services.retrieval_service.HybridRetriever") as mock_cls,
    ):
        mock_emb = MagicMock()
        mock_emb.model_name = "Qwen/Qwen3-Embedding-0.6B"
        mock_emb.model_rev = "main"
        mock_emb.embedding_dim = 1024
        mock_emb.embed = MagicMock(return_value=query_vec)
        mock_factory.return_value = mock_emb

        mock_retriever = AsyncMock()
        mock_retriever.retrieve = AsyncMock(return_value=[])
        mock_cls.return_value = mock_retriever

        await svc.query(_make_req())

    expected_hash = hashlib.sha256(json.dumps(query_vec, default=str).encode()).hexdigest()
    runs = [o for o in added_objects if isinstance(o, RetrievalRun)]
    assert runs[0].query_vector_hash == expected_hash


@pytest.mark.asyncio
async def test_service_passes_expected_model_to_retriever() -> None:
    from app.services.retrieval_service import RetrievalService

    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.add = MagicMock()
    session.flush = AsyncMock()

    svc = RetrievalService(session)

    with (
        patch("app.services.retrieval_service._get_embedding_service") as mock_factory,
        patch("app.services.retrieval_service.HybridRetriever") as mock_cls,
    ):
        mock_emb = MagicMock()
        mock_emb.model_name = "Qwen/Qwen3-Embedding-0.6B"
        mock_emb.model_rev = "main"
        mock_emb.embedding_dim = 1024
        mock_emb.embed = MagicMock(return_value=[0.0] * 1024)
        mock_factory.return_value = mock_emb

        mock_retriever = AsyncMock()
        mock_retriever.retrieve = AsyncMock(return_value=[])
        mock_cls.return_value = mock_retriever

        await svc.query(_make_req())

    mock_cls.assert_called_once()
    _, kwargs = mock_cls.call_args
    assert kwargs.get("expected_model") == "Qwen/Qwen3-Embedding-0.6B"
    assert kwargs.get("expected_dim") == 1024


@pytest.mark.asyncio
async def test_service_stores_plant_id_in_run() -> None:
    from app.models.retrieval_run import RetrievalRun
    from app.services.retrieval_service import RetrievalService

    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    added_objects = []
    session.add = MagicMock(side_effect=added_objects.append)
    session.flush = AsyncMock()

    pid = uuid.uuid4()
    svc = RetrievalService(session)

    with (
        patch("app.services.retrieval_service._get_embedding_service") as mock_factory,
        patch("app.services.retrieval_service.HybridRetriever") as mock_cls,
    ):
        mock_emb = MagicMock()
        mock_emb.model_name = "Qwen/Qwen3-Embedding-0.6B"
        mock_emb.model_rev = "main"
        mock_emb.embedding_dim = 1024
        mock_emb.embed = MagicMock(return_value=[0.0] * 1024)
        mock_factory.return_value = mock_emb

        mock_retriever = AsyncMock()
        mock_retriever.retrieve = AsyncMock(return_value=[])
        mock_cls.return_value = mock_retriever

        await svc.query(_make_req(plant_id=pid))

    runs = [o for o in added_objects if isinstance(o, RetrievalRun)]
    assert runs[0].plant_id == pid
