"""TICKET-047 — Chunk build idempotency tests."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.chunk_build_service import ChunkBuildService


def _mock_session():
    sess = MagicMock()
    sess.execute = AsyncMock()
    sess.flush = AsyncMock()
    sess.add = MagicMock()
    sess.get = AsyncMock()
    return sess


def _mock_emb(dim: int = 1024) -> MagicMock:
    emb = MagicMock()
    emb.model_name = "Qwen/Qwen3-Embedding-0.6B"
    emb.embedding_dim = dim
    emb.embed_batch = MagicMock(return_value=[[1.0 / (dim ** 0.5)] * dim])
    return emb


def _make_entry():
    e = MagicMock()
    e.id = uuid.uuid4()
    return e


def _scalar_none():
    r = MagicMock()
    r.scalars.return_value.all.return_value = []
    r.scalar_one_or_none.return_value = None
    return r


@pytest.mark.asyncio
async def test_skip_when_text_unchanged_and_embedding_current() -> None:
    entry = _make_entry()
    sess = _mock_session()
    sess.get.return_value = entry
    sess.execute.return_value = _scalar_none()

    existing_doc = MagicMock()
    existing_doc.text_hash = "same-hash"
    existing_doc.id = uuid.uuid4()

    chunks_built = [MagicMock(chunk_kind="identity", text="text", text_hash="same-hash")]

    from unittest.mock import patch

    with patch("app.services.chunk_build_service.build_all_chunks", return_value=chunks_built):
        svc = ChunkBuildService(session=sess, embedding_service=_mock_emb())
        svc._get_doc = AsyncMock(return_value=existing_doc)
        svc._is_embedding_current = AsyncMock(return_value=True)
        summary = await svc.build_for_entry(entry.id)

    assert summary.skipped == 1
    assert summary.updated == 0
    assert summary.inserted == 0


@pytest.mark.asyncio
async def test_rebuild_when_text_unchanged_but_embedding_stale() -> None:
    entry = _make_entry()
    sess = _mock_session()
    sess.get.return_value = entry
    sess.execute.return_value = _scalar_none()

    existing_doc = MagicMock()
    existing_doc.text_hash = "same-hash"
    existing_doc.id = uuid.uuid4()

    chunks_built = [MagicMock(chunk_kind="identity", text="text", text_hash="same-hash")]

    from unittest.mock import patch

    with patch("app.services.chunk_build_service.build_all_chunks", return_value=chunks_built):
        svc = ChunkBuildService(session=sess, embedding_service=_mock_emb())
        svc._get_doc = AsyncMock(return_value=existing_doc)
        svc._is_embedding_current = AsyncMock(return_value=False)
        svc._upsert_embedding = AsyncMock()
        sess.flush = AsyncMock()
        summary = await svc.build_for_entry(entry.id)

    assert summary.updated == 1
    assert summary.skipped == 0


@pytest.mark.asyncio
async def test_is_embedding_current_true_when_model_and_dim_match() -> None:
    sess = _mock_session()
    from app.models.plant_chunk_embedding import PlantChunkEmbedding

    fake_emb = MagicMock(spec=PlantChunkEmbedding)
    fake_emb.model_name = "Qwen/Qwen3-Embedding-0.6B"
    fake_emb.vector_dim = 1024
    r = MagicMock()
    r.scalar_one_or_none.return_value = fake_emb
    sess.execute.return_value = r

    emb_svc = _mock_emb(dim=1024)
    emb_svc.model_name = "Qwen/Qwen3-Embedding-0.6B"
    emb_svc.embedding_dim = 1024
    svc = ChunkBuildService(session=sess, embedding_service=emb_svc)
    doc = MagicMock()
    doc.id = uuid.uuid4()

    assert await svc._is_embedding_current(doc) is True


@pytest.mark.asyncio
async def test_is_embedding_current_false_when_model_differs() -> None:
    sess = _mock_session()
    from app.models.plant_chunk_embedding import PlantChunkEmbedding

    fake_emb = MagicMock(spec=PlantChunkEmbedding)
    fake_emb.model_name = "old-model"
    fake_emb.vector_dim = 1024
    r = MagicMock()
    r.scalar_one_or_none.return_value = fake_emb
    sess.execute.return_value = r

    emb_svc = _mock_emb()
    emb_svc.model_name = "Qwen/Qwen3-Embedding-0.6B"
    emb_svc.embedding_dim = 1024
    svc = ChunkBuildService(session=sess, embedding_service=emb_svc)
    doc = MagicMock()
    doc.id = uuid.uuid4()

    assert await svc._is_embedding_current(doc) is False


@pytest.mark.asyncio
async def test_is_embedding_current_false_when_dim_differs() -> None:
    sess = _mock_session()
    from app.models.plant_chunk_embedding import PlantChunkEmbedding

    fake_emb = MagicMock(spec=PlantChunkEmbedding)
    fake_emb.model_name = "Qwen/Qwen3-Embedding-0.6B"
    fake_emb.vector_dim = 384
    r = MagicMock()
    r.scalar_one_or_none.return_value = fake_emb
    sess.execute.return_value = r

    emb_svc = _mock_emb()
    emb_svc.model_name = "Qwen/Qwen3-Embedding-0.6B"
    emb_svc.embedding_dim = 1024
    svc = ChunkBuildService(session=sess, embedding_service=emb_svc)
    doc = MagicMock()
    doc.id = uuid.uuid4()

    assert await svc._is_embedding_current(doc) is False


@pytest.mark.asyncio
async def test_is_embedding_current_false_when_no_embedding() -> None:
    sess = _mock_session()
    r = MagicMock()
    r.scalar_one_or_none.return_value = None
    sess.execute.return_value = r

    svc = ChunkBuildService(session=sess, embedding_service=_mock_emb())
    doc = MagicMock()
    doc.id = uuid.uuid4()

    assert await svc._is_embedding_current(doc) is False
