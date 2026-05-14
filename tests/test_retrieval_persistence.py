"""TICKET-048 — RetrievalRun model and repository tests (no DB)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.retrieval_run_repository import RetrievalRunRepository
from app.repositories.retrieved_chunk_repository import RetrievedChunkRepository


def test_retrieval_run_has_embedding_model_rev_field() -> None:
    from app.models.retrieval_run import RetrievalRun

    assert hasattr(RetrievalRun, "embedding_model_rev")


def test_retrieval_run_has_query_vector_hash_field() -> None:
    from app.models.retrieval_run import RetrievalRun

    assert hasattr(RetrievalRun, "query_vector_hash")


def test_retrieval_run_has_plant_id_field() -> None:
    from app.models.retrieval_run import RetrievalRun

    assert hasattr(RetrievalRun, "plant_id")


def test_retrieval_run_has_chunk_builder_version_field() -> None:
    from app.models.retrieval_run import RetrievalRun

    assert hasattr(RetrievalRun, "chunk_builder_version")


@pytest.mark.asyncio
async def test_retrieval_run_repository_get_by_request_id() -> None:
    session = AsyncMock()
    run_id = uuid.uuid4()
    mock_run = MagicMock()
    session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_run))
    )

    repo = RetrievalRunRepository(session)
    result = await repo.get_by_request_id(run_id)
    assert result is mock_run


@pytest.mark.asyncio
async def test_retrieved_chunk_repository_list_by_run() -> None:
    session = AsyncMock()
    run_id = uuid.uuid4()
    mock_chunks = [MagicMock(), MagicMock()]
    session.execute = AsyncMock(
        return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=mock_chunks))))
    )

    repo = RetrievedChunkRepository(session)
    result = await repo.list_by_run(run_id)
    assert result == mock_chunks


def test_migration_0012_exists() -> None:
    from pathlib import Path

    m = Path("alembic/versions/0012_ticket48_retrieval_qwen_fields.py")
    assert m.exists()


def test_migration_0012_adds_expected_columns() -> None:
    from pathlib import Path

    src = Path("alembic/versions/0012_ticket48_retrieval_qwen_fields.py").read_text(encoding="utf-8")
    assert "embedding_model_rev" in src
    assert "query_vector_hash" in src
    assert "chunk_builder_version" in src
    assert "plant_id" in src
    assert "def upgrade" in src
    assert "def downgrade" in src
