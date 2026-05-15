"""TICKET-060A1 — SpeciesCandidateItem catalog contract extension tests."""

from __future__ import annotations

import uuid

import pytest

from app.schemas.plants import SpeciesCandidateItem

_SPECIES_ID = uuid.uuid4()

_BASE = dict(
    label_ko="몬스테라",
    label_en="Monstera",
    scientific_name="Monstera deliciosa",
    confidence=0.92,
    confidence_label="high",
    source="mock",
)


# ---------------------------------------------------------------------------
# Default values — backward-compatible
# ---------------------------------------------------------------------------

def test_new_fields_have_safe_defaults() -> None:
    item = SpeciesCandidateItem(**_BASE)
    assert item.display_name is None
    assert item.catalog_matched is False
    assert item.raw_label is None
    assert item.match_reason is None


def test_existing_fields_unchanged() -> None:
    item = SpeciesCandidateItem(**_BASE)
    assert item.label_ko == "몬스테라"
    assert item.label_en == "Monstera"
    assert item.scientific_name == "Monstera deliciosa"
    assert item.confidence == 0.92
    assert item.confidence_label == "high"
    assert item.source == "mock"
    assert item.species_profile_id is None


# ---------------------------------------------------------------------------
# New fields round-trip
# ---------------------------------------------------------------------------

def test_display_name_set_and_serialized() -> None:
    item = SpeciesCandidateItem(**_BASE, display_name="몬스테라 델리시오사")
    assert item.display_name == "몬스테라 델리시오사"
    d = item.model_dump()
    assert d["display_name"] == "몬스테라 델리시오사"


def test_catalog_matched_true() -> None:
    item = SpeciesCandidateItem(**_BASE, catalog_matched=True)
    assert item.catalog_matched is True
    assert item.model_dump()["catalog_matched"] is True


def test_raw_label_set_and_serialized() -> None:
    item = SpeciesCandidateItem(**_BASE, raw_label="Monstera deliciosa")
    assert item.raw_label == "Monstera deliciosa"
    assert item.model_dump()["raw_label"] == "Monstera deliciosa"


@pytest.mark.parametrize("reason", [
    "scientific_name_exact",
    "korean_name_exact",
    "common_name_exact",
    "normalized",
    "alias",
    "catalog_default",
    "unmatched",
])
def test_match_reason_accepts_all_defined_values(reason: str) -> None:
    item = SpeciesCandidateItem(**_BASE, match_reason=reason)
    assert item.match_reason == reason


# ---------------------------------------------------------------------------
# species_profile_id semantics
# ---------------------------------------------------------------------------

def test_species_profile_id_none_means_not_registerable() -> None:
    item = SpeciesCandidateItem(**_BASE, species_profile_id=None)
    assert item.species_profile_id is None


def test_species_profile_id_set_means_registerable() -> None:
    item = SpeciesCandidateItem(**_BASE, species_profile_id=_SPECIES_ID)
    assert item.species_profile_id == _SPECIES_ID


def test_catalog_matched_and_profile_id_independent() -> None:
    """catalog_matched and species_profile_id are independent fields."""
    item = SpeciesCandidateItem(**_BASE, catalog_matched=True, species_profile_id=None)
    assert item.catalog_matched is True
    assert item.species_profile_id is None


# ---------------------------------------------------------------------------
# JSON serialization includes new fields
# ---------------------------------------------------------------------------

def test_model_dump_includes_all_new_fields() -> None:
    item = SpeciesCandidateItem(
        **_BASE,
        species_profile_id=_SPECIES_ID,
        display_name="몬스테라",
        catalog_matched=True,
        raw_label="Monstera deliciosa",
        match_reason="scientific_name_exact",
    )
    d = item.model_dump()
    assert "display_name" in d
    assert "catalog_matched" in d
    assert "raw_label" in d
    assert "match_reason" in d


def test_model_dump_new_fields_present_even_when_none() -> None:
    item = SpeciesCandidateItem(**_BASE)
    d = item.model_dump()
    assert "display_name" in d
    assert "catalog_matched" in d
    assert "raw_label" in d
    assert "match_reason" in d
