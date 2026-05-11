"""TICKET-014A — PlantKnowledgeIngestService pure-logic tests (no DB)."""

from __future__ import annotations

import hashlib
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.plant_knowledge import IngestSummary
from app.services.plant_knowledge_ingest_service import (
    _bool_from_text,
    _build_col_index,
    _parse_pest_terms,
    _row_hash,
    _str,
)

# ---------------------------------------------------------------------------
# Pure helper functions
# ---------------------------------------------------------------------------


def test_str_strips_whitespace() -> None:
    assert _str("  몬스테라  ") == "몬스테라"
    assert _str("") is None
    assert _str(None) is None
    assert _str(42) == "42"


def test_bool_from_text() -> None:
    assert _bool_from_text("유") is True
    assert _bool_from_text("있음") is True
    assert _bool_from_text("무") is False
    assert _bool_from_text("없음") is False
    assert _bool_from_text("") is None
    assert _bool_from_text(None) is None
    assert _bool_from_text("모름") is None


def test_parse_pest_terms_splits_correctly() -> None:
    terms = _parse_pest_terms("진딧물, 응애, 깍지벌레")
    assert set(terms) == {"진딧물", "응애", "깍지벌레"}


def test_parse_pest_terms_empty_input() -> None:
    assert _parse_pest_terms(None) == []
    assert _parse_pest_terms("") == []


def test_parse_pest_terms_newline_delimiter() -> None:
    terms = _parse_pest_terms("진딧물\n응애")
    assert "진딧물" in terms
    assert "응애" in terms


def test_row_hash_is_sha256_hex() -> None:
    h = _row_hash(["a", "b", None])
    expected = hashlib.sha256(b"a|b|").hexdigest()
    assert h == expected


def test_row_hash_changes_on_content_change() -> None:
    h1 = _row_hash(["a", "b"])
    h2 = _row_hash(["a", "c"])
    assert h1 != h2


def test_row_hash_same_for_identical_rows() -> None:
    assert _row_hash(["x", "y", "z"]) == _row_hash(["x", "y", "z"])


# ---------------------------------------------------------------------------
# Column index builder
# ---------------------------------------------------------------------------


def test_build_col_index_finds_korean_header() -> None:
    headers = ["식물명", "학명", "고유번호"]
    index = _build_col_index(headers)
    assert index["korean_name"] == 0
    assert index["scientific_name"] == 1
    assert index["nongsaro_id"] == 2


def test_build_col_index_case_insensitive() -> None:
    headers = ["Scientific Name", "ID"]
    index = _build_col_index(headers)
    assert "scientific_name" in index
    assert "nongsaro_id" in index


def test_build_col_index_missing_header_absent() -> None:
    index = _build_col_index(["알 수 없는 컬럼"])
    assert "korean_name" not in index


# ---------------------------------------------------------------------------
# IngestSummary dataclass
# ---------------------------------------------------------------------------


def test_ingest_summary_defaults() -> None:
    s = IngestSummary(source_file="test.xlsx")
    assert s.total_rows == 0
    assert s.inserted == 0
    assert s.errors == 0
    assert s.error_details == []


# ---------------------------------------------------------------------------
# Service: no embedding / vector imports
# ---------------------------------------------------------------------------


def test_service_does_not_import_pgvector() -> None:
    import app.services.plant_knowledge_ingest_service as mod

    src = open(mod.__file__, encoding="utf-8").read()
    for forbidden in ("pgvector", "embedding", "openai", "anthropic", "torch"):
        assert forbidden not in src, f"Forbidden: {forbidden!r} in service"


# ---------------------------------------------------------------------------
# Service: _process_row with mocked session (insert path)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_row_insert_returns_inserted() -> None:
    from app.services.plant_knowledge_ingest_service import PlantKnowledgeIngestService

    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    svc = PlantKnowledgeIngestService(session)
    svc._find_entry = AsyncMock(return_value=None)
    svc._insert_children = AsyncMock()
    svc._add_source = AsyncMock()

    headers = ["고유번호", "식물명", "학명"]
    col_index = _build_col_index(headers)
    raw_row = ("K001", "몬스테라", "Monstera deliciosa")

    status = await svc._process_row(
        raw_row=raw_row,
        col_index=col_index,
        row_number=2,
        source_file="test.xlsx",
    )
    assert status == "inserted"
    session.add.assert_called_once()
    svc._insert_children.assert_called_once()
    svc._add_source.assert_called_once()


@pytest.mark.asyncio
async def test_process_row_ignored_when_hash_unchanged() -> None:
    from app.models.plant_knowledge_entry import PlantKnowledgeEntry
    from app.models.plant_knowledge_source import PlantKnowledgeSource
    from app.services.plant_knowledge_ingest_service import PlantKnowledgeIngestService

    session = AsyncMock()
    svc = PlantKnowledgeIngestService(session)

    raw_row = ("K001", "몬스테라", "Monstera deliciosa")
    existing_hash = _row_hash(list(raw_row))

    fake_entry = MagicMock(spec=PlantKnowledgeEntry)
    fake_entry.id = uuid.uuid4()
    fake_source = MagicMock(spec=PlantKnowledgeSource)
    fake_source.source_row_hash = existing_hash

    svc._find_entry = AsyncMock(return_value=fake_entry)
    svc._find_latest_source = AsyncMock(return_value=fake_source)

    headers = ["고유번호", "식물명", "학명"]
    col_index = _build_col_index(headers)
    status = await svc._process_row(
        raw_row=raw_row,
        col_index=col_index,
        row_number=2,
        source_file="test.xlsx",
    )
    assert status == "ignored"


@pytest.mark.asyncio
async def test_process_row_updated_when_hash_changed() -> None:
    from app.models.plant_knowledge_entry import PlantKnowledgeEntry
    from app.models.plant_knowledge_source import PlantKnowledgeSource
    from app.services.plant_knowledge_ingest_service import PlantKnowledgeIngestService

    session = AsyncMock()
    svc = PlantKnowledgeIngestService(session)

    raw_row = ("K001", "몬스테라_변경", "Monstera deliciosa")
    fake_entry = MagicMock(spec=PlantKnowledgeEntry)
    fake_entry.id = uuid.uuid4()
    fake_source = MagicMock(spec=PlantKnowledgeSource)
    fake_source.source_row_hash = "old_hash_that_does_not_match"

    svc._find_entry = AsyncMock(return_value=fake_entry)
    svc._find_latest_source = AsyncMock(return_value=fake_source)
    svc._update_children = AsyncMock()
    svc._add_source = AsyncMock()

    headers = ["고유번호", "식물명", "학명"]
    col_index = _build_col_index(headers)
    status = await svc._process_row(
        raw_row=raw_row,
        col_index=col_index,
        row_number=2,
        source_file="test.xlsx",
    )
    assert status == "updated"
    svc._update_children.assert_called_once()
    svc._add_source.assert_called_once()


@pytest.mark.asyncio
async def test_process_row_raises_when_no_nongsaro_id() -> None:
    from app.services.plant_knowledge_ingest_service import PlantKnowledgeIngestService

    session = AsyncMock()
    svc = PlantKnowledgeIngestService(session)

    raw_row = (None, "몬스테라")  # no nongsaro_id
    with pytest.raises(ValueError, match="nongsaro_id"):
        await svc._process_row(
            raw_row=raw_row,
            col_index={},
            row_number=2,
            source_file="test.xlsx",
        )


# ---------------------------------------------------------------------------
# Migration: alembic file exists and is syntactically valid
# ---------------------------------------------------------------------------


def test_migration_file_exists() -> None:
    from pathlib import Path

    migration = Path("alembic/versions/0003_ticket14a_plant_knowledge_tables.py")
    assert migration.exists(), "Migration 0003 not found"


def test_migration_has_upgrade_and_downgrade() -> None:
    from pathlib import Path

    src = Path("alembic/versions/0003_ticket14a_plant_knowledge_tables.py").read_text(encoding="utf-8")
    assert "def upgrade" in src
    assert "def downgrade" in src
    assert "plant_knowledge_entries" in src
    assert "plant_pest_references" in src
