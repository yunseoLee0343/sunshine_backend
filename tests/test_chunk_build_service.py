"""Unit tests for ChunkBuildService — TICKET-014G coverage."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.chunk_build_service import ChunkBuildService


def _mock_session():
    sess = MagicMock()
    sess.execute = AsyncMock()
    sess.flush = AsyncMock()
    sess.add = MagicMock()
    sess.get = AsyncMock()
    return sess


def _mock_emb(dim: int = 4):
    emb = MagicMock()
    emb.model_name = "test-model"
    emb.embedding_dim = dim
    emb.embed_batch = MagicMock(return_value=[[0.1] * dim])
    return emb


def _make_entry(entry_id: uuid.UUID | None = None):
    e = MagicMock()
    e.id = entry_id or uuid.uuid4()
    return e


def _scalar_result(value):
    r = MagicMock()
    r.scalars.return_value.all.return_value = [value] if value is not None else []
    r.scalar_one_or_none.return_value = value
    return r


# ---------------------------------------------------------------------------
# build_for_entry — entry not found
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_for_entry_not_found_returns_error():
    sess = _mock_session()
    sess.get.return_value = None
    svc = ChunkBuildService(session=sess, embedding_service=_mock_emb())

    summary = await svc.build_for_entry(uuid.uuid4())

    assert summary.total_entries == 0
    assert summary.errors == 1
    assert len(summary.error_details) == 1


# ---------------------------------------------------------------------------
# build_for_entry — new chunks inserted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_for_entry_inserts_new_chunks():
    entry = _make_entry()
    sess = _mock_session()
    sess.get.return_value = entry

    # _get_one returns None for all sub-models
    # _get_doc returns None → new doc
    # _upsert_embedding: first execute returns None (no existing embedding)
    sess.execute.return_value = _scalar_result(None)

    chunks_built = [
        MagicMock(chunk_kind="care_overview", text="care text", text_hash="h1"),
    ]

    with patch("app.services.chunk_build_service.build_all_chunks", return_value=chunks_built):
        svc = ChunkBuildService(session=sess, embedding_service=_mock_emb())
        summary = await svc.build_for_entry(entry.id)

    assert summary.inserted == 1
    assert summary.skipped == 0
    assert summary.errors == 0


# ---------------------------------------------------------------------------
# build_for_entry — unchanged chunk skipped
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_for_entry_skips_unchanged_chunk():
    entry = _make_entry()
    sess = _mock_session()
    sess.get.return_value = entry

    existing_doc = MagicMock()
    existing_doc.text_hash = "same-hash"
    existing_doc.id = uuid.uuid4()

    # _get_one returns None; _get_doc returns existing with same hash
    def _side_effect(query):
        r = MagicMock()
        r.scalars.return_value.all.return_value = []
        r.scalar_one_or_none.return_value = existing_doc
        return r

    sess.execute.side_effect = _side_effect

    chunks_built = [MagicMock(chunk_kind="care_overview", text="care", text_hash="same-hash")]

    with patch("app.services.chunk_build_service.build_all_chunks", return_value=chunks_built):
        svc = ChunkBuildService(session=sess, embedding_service=_mock_emb())
        svc._is_embedding_current = AsyncMock(return_value=True)
        summary = await svc.build_for_entry(entry.id)

    assert summary.skipped == 1
    assert summary.inserted == 0


# ---------------------------------------------------------------------------
# build_for_entry — updated chunk (same doc, different hash)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_for_entry_updates_changed_chunk():
    entry = _make_entry()
    sess = _mock_session()
    sess.get.return_value = entry

    existing_doc = MagicMock()
    existing_doc.text_hash = "old-hash"
    existing_doc.id = uuid.uuid4()

    call_count = 0

    def _side_effect(query):
        nonlocal call_count
        call_count += 1
        r = MagicMock()
        r.scalars.return_value.all.return_value = []
        # First 5 calls are _get_one (returns None); 6th is _get_doc (returns existing)
        # 7th call is _upsert_embedding (returns None = no existing embedding)
        if call_count <= 5:
            r.scalar_one_or_none.return_value = None
        elif call_count == 6:
            r.scalar_one_or_none.return_value = existing_doc
        else:
            r.scalar_one_or_none.return_value = None
        return r

    sess.execute.side_effect = _side_effect

    chunks_built = [MagicMock(chunk_kind="care_overview", text="new care", text_hash="new-hash")]

    with patch("app.services.chunk_build_service.build_all_chunks", return_value=chunks_built):
        svc = ChunkBuildService(session=sess, embedding_service=_mock_emb())
        summary = await svc.build_for_entry(entry.id)

    assert summary.updated == 1
    assert existing_doc.text_hash == "new-hash"


# ---------------------------------------------------------------------------
# build_for_entry — exception in _build_entry is captured
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_for_entry_captures_exception():
    entry = _make_entry()
    sess = _mock_session()
    sess.get.return_value = entry
    sess.execute.side_effect = RuntimeError("DB exploded")

    svc = ChunkBuildService(session=sess, embedding_service=_mock_emb())
    summary = await svc.build_for_entry(entry.id)

    assert summary.errors == 1
    assert "DB exploded" in summary.error_details[0]


# ---------------------------------------------------------------------------
# build_all — iterates over all entries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_all_processes_all_entries():
    entry_a = _make_entry()
    entry_b = _make_entry()

    sess = _mock_session()
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [entry_a, entry_b]
    sess.execute.return_value = list_result

    with patch.object(ChunkBuildService, "_build_entry", new=AsyncMock()) as mock_build:
        svc = ChunkBuildService(session=sess, embedding_service=_mock_emb())
        summary = await svc.build_all()

    assert summary.total_entries == 2
    assert mock_build.call_count == 2


# ---------------------------------------------------------------------------
# _upsert_embedding — updates existing embedding row
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_embedding_updates_existing():
    sess = _mock_session()
    existing_emb = MagicMock()
    existing_emb.vector = [0.0] * 4
    existing_emb.vector_dim = 4

    r = MagicMock()
    r.scalar_one_or_none.return_value = existing_emb
    sess.execute.return_value = r

    emb_svc = _mock_emb()
    svc = ChunkBuildService(session=sess, embedding_service=emb_svc)

    doc = MagicMock()
    doc.id = uuid.uuid4()
    new_vec = [0.9, 0.8, 0.7, 0.6]
    now = datetime.now(UTC)

    await svc._upsert_embedding(doc, new_vec, now)

    assert existing_emb.vector == new_vec
    assert existing_emb.vector_dim == 4
    assert existing_emb.model_name == emb_svc.model_name
    sess.flush.assert_called_once()
