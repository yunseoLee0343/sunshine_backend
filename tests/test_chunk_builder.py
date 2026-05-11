"""TICKET-014B — chunk_builder pure-logic tests (no DB, no model load)."""

from __future__ import annotations

import hashlib
import uuid
from unittest.mock import MagicMock

import pytest

from app.domain.chunk import CHUNK_KINDS, ChunkBuildSummary
from app.embedding.chunk_builder import (
    _hash,
    _join_lines,
    _line,
    build_all_chunks,
    build_care_requirement,
    build_identity,
    build_pest_reference,
    build_placement,
    build_seasonal_watering,
    build_visual_trait,
)
from app.models.plant_care_requirement import PlantCareRequirement
from app.models.plant_knowledge_entry import PlantKnowledgeEntry
from app.models.plant_pest_reference import PlantPestReference
from app.models.plant_placement import PlantPlacement
from app.models.plant_seasonal_watering import PlantSeasonalWatering
from app.models.plant_visual_trait import PlantVisualTrait

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entry(**kwargs) -> PlantKnowledgeEntry:
    e = MagicMock(spec=PlantKnowledgeEntry)
    e.id = kwargs.get("id", uuid.uuid4())
    e.korean_name = kwargs.get("korean_name", "몬스테라")
    e.scientific_name = kwargs.get("scientific_name", "Monstera deliciosa")
    e.common_name = kwargs.get("common_name", None)
    e.family = kwargs.get("family", None)
    e.origin = kwargs.get("origin", None)
    return e


# ---------------------------------------------------------------------------
# _hash
# ---------------------------------------------------------------------------


def test_hash_is_sha256() -> None:
    text = "hello"
    assert _hash(text) == hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_hash_differs_for_different_text() -> None:
    assert _hash("a") != _hash("b")


# ---------------------------------------------------------------------------
# _line
# ---------------------------------------------------------------------------


def test_line_returns_formatted_string() -> None:
    assert _line("광요구도", "강광") == "광요구도: 강광."


def test_line_returns_empty_when_none() -> None:
    assert _line("광요구도", None) == ""


def test_line_returns_empty_when_blank() -> None:
    assert _line("광요구도", "   ") == ""


# ---------------------------------------------------------------------------
# _join_lines
# ---------------------------------------------------------------------------


def test_join_lines_skips_empty_strings() -> None:
    result = _join_lines("a", "", "b", "")
    assert result == "a b"


# ---------------------------------------------------------------------------
# build_identity
# ---------------------------------------------------------------------------


def test_build_identity_includes_korean_and_scientific() -> None:
    e = _entry(korean_name="몬스테라", scientific_name="Monstera deliciosa")
    text = build_identity(e)
    assert "몬스테라" in text
    assert "Monstera deliciosa" in text
    assert "식물입니다" in text


def test_build_identity_no_scientific_name() -> None:
    e = _entry(scientific_name=None)
    text = build_identity(e)
    assert "(" not in text


def test_build_identity_includes_optional_fields() -> None:
    e = _entry(common_name="Swiss Cheese Plant", family="천남성과", origin="멕시코")
    text = build_identity(e)
    assert "Swiss Cheese Plant" in text
    assert "천남성과" in text
    assert "멕시코" in text


def test_build_identity_omits_none_optional_fields() -> None:
    e = _entry(common_name=None, family=None, origin=None)
    text = build_identity(e)
    assert "영문명" not in text
    assert "과명" not in text
    assert "원산지" not in text


# ---------------------------------------------------------------------------
# build_care_requirement
# ---------------------------------------------------------------------------


def test_build_care_requirement_with_data() -> None:
    e = _entry()
    care = MagicMock(spec=PlantCareRequirement)
    care.growth_temp_text = "18~25°C"
    care.light_requirement = "강광"
    care.watering_frequency = "주 1회"
    care.soil_type = "배수성 좋은 흙"
    care.fertilizer_info = "월 1회"
    text = build_care_requirement(e, care)
    assert "18~25°C" in text
    assert "강광" in text
    assert "주 1회" in text


def test_build_care_requirement_none_returns_fallback() -> None:
    e = _entry()
    text = build_care_requirement(e, None)
    assert "관리 정보가 없습니다" in text


def test_build_care_requirement_omits_none_fields() -> None:
    e = _entry()
    care = MagicMock(spec=PlantCareRequirement)
    care.growth_temp_text = None
    care.light_requirement = "강광"
    care.watering_frequency = None
    care.soil_type = None
    care.fertilizer_info = None
    text = build_care_requirement(e, care)
    assert "생육온도" not in text
    assert "강광" in text


# ---------------------------------------------------------------------------
# build_seasonal_watering
# ---------------------------------------------------------------------------


def test_build_seasonal_watering_with_all_seasons() -> None:
    e = _entry()
    w = MagicMock(spec=PlantSeasonalWatering)
    w.spring = "주 2회"
    w.summer = "주 3회"
    w.autumn = "주 1회"
    w.winter = "2주 1회"
    text = build_seasonal_watering(e, w)
    assert "봄" in text
    assert "여름" in text
    assert "가을" in text
    assert "겨울" in text


def test_build_seasonal_watering_none_returns_fallback() -> None:
    text = build_seasonal_watering(_entry(), None)
    assert "계절별 물주기 정보가 없습니다" in text


# ---------------------------------------------------------------------------
# build_pest_reference
# ---------------------------------------------------------------------------


def test_build_pest_reference_includes_terms() -> None:
    e = _entry()
    p = MagicMock(spec=PlantPestReference)
    p.pest_text = "진딧물, 응애"
    p.disease_text = "흰가루병"
    p.parsed_pest_terms = ["진딧물", "응애"]
    text = build_pest_reference(e, p)
    assert "진딧물" in text
    assert "흰가루병" in text


def test_build_pest_reference_none_terms_omitted() -> None:
    e = _entry()
    p = MagicMock(spec=PlantPestReference)
    p.pest_text = "응애"
    p.disease_text = None
    p.parsed_pest_terms = []
    text = build_pest_reference(e, p)
    assert "관련 해충 목록" not in text


def test_build_pest_reference_none_returns_fallback() -> None:
    assert "병충해 정보가 없습니다" in build_pest_reference(_entry(), None)


# ---------------------------------------------------------------------------
# build_visual_trait
# ---------------------------------------------------------------------------


def test_build_visual_trait_with_data() -> None:
    e = _entry()
    v = MagicMock(spec=PlantVisualTrait)
    v.leaf_color = "녹색"
    v.leaf_shape = "심장형"
    v.flower_color = None
    v.flower_season = None
    v.height_text = "50~100cm"
    text = build_visual_trait(e, v)
    assert "녹색" in text
    assert "심장형" in text
    assert "50~100cm" in text
    assert "꽃 색상" not in text


def test_build_visual_trait_none_returns_fallback() -> None:
    assert "외형 정보가 없습니다" in build_visual_trait(_entry(), None)


# ---------------------------------------------------------------------------
# build_placement
# ---------------------------------------------------------------------------


def test_build_placement_toxic_true() -> None:
    e = _entry()
    pl = MagicMock(spec=PlantPlacement)
    pl.placement_locations = "실내"
    pl.is_toxic = True
    pl.toxicity_detail = "반려동물에게 유해"
    pl.fragrance = None
    text = build_placement(e, pl)
    assert "독성: 있음" in text
    assert "반려동물에게 유해" in text


def test_build_placement_toxic_false() -> None:
    e = _entry()
    pl = MagicMock(spec=PlantPlacement)
    pl.placement_locations = None
    pl.is_toxic = False
    pl.toxicity_detail = None
    pl.fragrance = None
    text = build_placement(e, pl)
    assert "독성: 없음" in text


def test_build_placement_toxic_none_omits_label() -> None:
    e = _entry()
    pl = MagicMock(spec=PlantPlacement)
    pl.placement_locations = None
    pl.is_toxic = None
    pl.toxicity_detail = None
    pl.fragrance = None
    text = build_placement(e, pl)
    assert "독성:" not in text


def test_build_placement_none_returns_fallback() -> None:
    assert "배치 정보가 없습니다" in build_placement(_entry(), None)


# ---------------------------------------------------------------------------
# build_all_chunks
# ---------------------------------------------------------------------------


def test_build_all_chunks_returns_six_chunks() -> None:
    e = _entry()
    chunks = build_all_chunks(e, None, None, None, None, None)
    assert len(chunks) == 6
    kinds = {c.chunk_kind for c in chunks}
    assert kinds == set(CHUNK_KINDS)


def test_build_all_chunks_text_hash_matches_content() -> None:
    e = _entry()
    chunks = build_all_chunks(e, None, None, None, None, None)
    for chunk in chunks:
        assert chunk.text_hash == _hash(chunk.text)


def test_build_all_chunks_plant_knowledge_id_propagated() -> None:
    eid = uuid.uuid4()
    e = _entry(id=eid)
    chunks = build_all_chunks(e, None, None, None, None, None)
    for chunk in chunks:
        assert chunk.plant_knowledge_id == eid


def test_build_all_chunks_are_frozen_dataclass() -> None:
    e = _entry()
    chunks = build_all_chunks(e, None, None, None, None, None)
    for chunk in chunks:
        with pytest.raises((AttributeError, TypeError)):
            chunk.text = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ChunkBuildSummary
# ---------------------------------------------------------------------------


def test_chunk_build_summary_defaults() -> None:
    s = ChunkBuildSummary()
    assert s.total_entries == 0
    assert s.inserted == 0
    assert s.updated == 0
    assert s.skipped == 0
    assert s.errors == 0
    assert s.error_details == []


# ---------------------------------------------------------------------------
# no forbidden imports in chunk_builder
# ---------------------------------------------------------------------------


def test_chunk_builder_has_no_forbidden_imports() -> None:
    import app.embedding.chunk_builder as mod

    src = open(mod.__file__, encoding="utf-8").read()
    for forbidden in ("openai", "anthropic", "pgvector", "torch", "requests"):
        assert forbidden not in src, f"Forbidden import: {forbidden!r}"


def test_local_embedding_service_has_no_api_calls() -> None:
    import app.embedding.local_embedding_service as mod

    src = open(mod.__file__, encoding="utf-8").read()
    for forbidden in ("openai", "anthropic", "requests", "httpx", "aiohttp"):
        assert forbidden not in src, f"Forbidden: {forbidden!r}"
