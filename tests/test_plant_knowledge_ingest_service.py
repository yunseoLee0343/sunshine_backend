"""TICKET-046 — PlantKnowledgeIngestService tests (updated Excel source)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.plant_knowledge_ingest_service import (
    COLUMN_MAP,
    _build_col_index,
)


def test_legacy_filename_absent_from_service_source() -> None:
    import app.services.plant_knowledge_ingest_service as mod

    src = open(mod.__file__, encoding="utf-8").read()
    assert "전체식물_농사로데이터" not in src


def test_new_seasonal_column_names_in_column_map() -> None:
    assert "물주기_봄" in COLUMN_MAP["spring_watering"]
    assert "물주기_여름" in COLUMN_MAP["summer_watering"]
    assert "물주기_가을" in COLUMN_MAP["autumn_watering"]
    assert "물주기_겨울" in COLUMN_MAP["winter_watering"]


def test_new_visual_column_names_in_column_map() -> None:
    assert "꽃색" in COLUMN_MAP["flower_color"]
    assert "꽃피는계절" in COLUMN_MAP["flower_season"]
    assert "잎형태" in COLUMN_MAP["leaf_shape"]
    assert "잎색" in COLUMN_MAP["leaf_color"]
    assert "성장높이(cm)" in COLUMN_MAP["height_text"]
    assert "배치장소" in COLUMN_MAP["placement_locations"]


def test_new_disease_column_name_in_column_map() -> None:
    assert "병충해관리" in COLUMN_MAP["disease_text"]


def test_col_index_resolves_new_seasonal_headers() -> None:
    headers = ["농사로ID", "한국명", "학명", "물주기_봄", "물주기_여름", "물주기_가을", "물주기_겨울"]
    idx = _build_col_index(headers)
    assert idx.get("spring_watering") == 3
    assert idx.get("summer_watering") == 4
    assert idx.get("autumn_watering") == 5
    assert idx.get("winter_watering") == 6


@pytest.mark.asyncio
async def test_process_row_rejects_empty_scientific_name() -> None:
    from app.services.plant_knowledge_ingest_service import PlantKnowledgeIngestService

    session = AsyncMock()
    svc = PlantKnowledgeIngestService(session)
    svc._find_entry = AsyncMock(return_value=None)

    col_index = _build_col_index(["농사로ID", "한국명", "학명"])
    raw_row = ("K001", "몬스테라", None)

    with pytest.raises(ValueError, match="scientific_name"):
        await svc._process_row(
            raw_row=raw_row,
            col_index=col_index,
            row_number=2,
            source_file="test.xlsx",
        )


@pytest.mark.asyncio
async def test_process_row_rejects_empty_string_scientific_name() -> None:
    from app.services.plant_knowledge_ingest_service import PlantKnowledgeIngestService

    session = AsyncMock()
    svc = PlantKnowledgeIngestService(session)
    svc._find_entry = AsyncMock(return_value=None)

    col_index = _build_col_index(["농사로ID", "한국명", "학명"])
    raw_row = ("K001", "몬스테라", "   ")

    with pytest.raises(ValueError, match="scientific_name"):
        await svc._process_row(
            raw_row=raw_row,
            col_index=col_index,
            row_number=2,
            source_file="test.xlsx",
        )


@pytest.mark.asyncio
async def test_process_row_updated_when_care_field_changes() -> None:
    from app.models.plant_knowledge_entry import PlantKnowledgeEntry
    from app.models.plant_knowledge_source import PlantKnowledgeSource
    from app.services.plant_knowledge_ingest_service import PlantKnowledgeIngestService

    session = AsyncMock()
    svc = PlantKnowledgeIngestService(session)

    raw_row = ("K001", "몬스테라", "Monstera deliciosa", "18~24℃")
    fake_entry = MagicMock(spec=PlantKnowledgeEntry)
    fake_entry.id = uuid.uuid4()
    fake_source = MagicMock(spec=PlantKnowledgeSource)
    fake_source.source_row_hash = "old_hash_different"

    svc._find_entry = AsyncMock(return_value=fake_entry)
    svc._find_latest_source = AsyncMock(return_value=fake_source)
    svc._update_children = AsyncMock()
    svc._add_source = AsyncMock()

    col_index = _build_col_index(["농사로ID", "한국명", "학명", "생육온도"])
    status = await svc._process_row(
        raw_row=raw_row,
        col_index=col_index,
        row_number=2,
        source_file="test.xlsx",
    )
    assert status == "updated"
    svc._update_children.assert_called_once()
    svc._add_source.assert_called_once()
