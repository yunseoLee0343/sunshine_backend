"""TICKET-047 — EmbeddingRepository tests."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.embedding_repository import EmbeddingRepository


def _mock_session():
    sess = MagicMock()
    sess.execute = AsyncMock()
    return sess


def _scalar_result(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    r.scalar_one.return_value = value
    r.scalars.return_value.all.return_value = value if isinstance(value, list) else [value]
    return r


@pytest.mark.asyncio
async def test_get_by_chunk_document_id_returns_embedding() -> None:
    from app.models.plant_chunk_embedding import PlantChunkEmbedding

    fake_emb = MagicMock(spec=PlantChunkEmbedding)
    sess = _mock_session()
    sess.execute.return_value = _scalar_result(fake_emb)

    repo = EmbeddingRepository(sess)
    result = await repo.get_by_chunk_document_id(uuid.uuid4())
    assert result is fake_emb


@pytest.mark.asyncio
async def test_get_by_chunk_document_id_returns_none_when_absent() -> None:
    sess = _mock_session()
    sess.execute.return_value = _scalar_result(None)

    repo = EmbeddingRepository(sess)
    result = await repo.get_by_chunk_document_id(uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_list_stale_returns_mismatched_rows() -> None:
    from app.models.plant_chunk_embedding import PlantChunkEmbedding

    stale1 = MagicMock(spec=PlantChunkEmbedding)
    stale2 = MagicMock(spec=PlantChunkEmbedding)
    sess = _mock_session()
    r = MagicMock()
    r.scalars.return_value.all.return_value = [stale1, stale2]
    sess.execute.return_value = r

    repo = EmbeddingRepository(sess)
    result = await repo.list_stale("Qwen/Qwen3-Embedding-0.6B", 1024)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_count_dim_mismatch_returns_integer() -> None:
    sess = _mock_session()
    r = MagicMock()
    r.scalar_one.return_value = 3
    sess.execute.return_value = r

    repo = EmbeddingRepository(sess)
    count = await repo.count_dim_mismatch(1024)
    assert count == 3


def test_embedding_repository_has_no_write_methods() -> None:
    """Read-only repo must not expose insert/update/delete methods."""
    repo_methods = {m for m in dir(EmbeddingRepository) if not m.startswith("_")}
    for forbidden in ("insert", "save", "upsert", "delete", "update", "add"):
        assert forbidden not in repo_methods, f"Write method found: {forbidden}"
