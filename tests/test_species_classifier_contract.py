"""TICKET-003 — SpeciesClassifierPort shape & SpeciesCandidate field contract."""

import asyncio
import inspect
from typing import get_type_hints

from app.vision.mock_species_classifier import MockSpeciesClassifier
from app.vision.species_classifier import SpeciesCandidate, SpeciesClassifierPort

# ---------------------------------------------------------------------------
# Port shape
# ---------------------------------------------------------------------------


def test_port_exists_and_is_protocol() -> None:
    assert hasattr(SpeciesClassifierPort, "classify_species")


def test_port_classify_species_signature() -> None:
    sig = inspect.signature(SpeciesClassifierPort.classify_species)
    params = sig.parameters
    assert "image_ref" in params
    assert "locale" in params
    assert "top_k" in params
    assert params["locale"].default == "ko-KR"
    assert params["top_k"].default == 3


def test_classify_species_is_async() -> None:
    # The mock satisfies the port — verify the method is awaitable.
    classifier = MockSpeciesClassifier()
    assert inspect.iscoroutinefunction(classifier.classify_species)


def test_classify_species_returns_list_of_candidates() -> None:
    classifier = MockSpeciesClassifier()
    result = asyncio.run(classifier.classify_species("uploads/mock/monstera.jpg"))
    assert isinstance(result, list)
    assert len(result) >= 1
    for c in result:
        assert isinstance(c, SpeciesCandidate)


# ---------------------------------------------------------------------------
# SpeciesCandidate field contract
# ---------------------------------------------------------------------------

ALLOWED_FIELDS = {
    "label_ko",
    "label_en",
    "scientific_name",
    "confidence",
    "confidence_label",
    "source",
}

FORBIDDEN_FIELDS = {
    "disease",
    "disease_prediction",
    "pest",
    "pest_prediction",
    "health",
    "health_prediction",
    "diagnosis",
    "treatment",
    "pesticide",
    "severity",
    "recommended_action",
}


def test_species_candidate_has_only_allowed_fields() -> None:
    fields = set(SpeciesCandidate.model_fields.keys())
    assert fields == ALLOWED_FIELDS, f"Unexpected fields: {fields ^ ALLOWED_FIELDS}"


def test_species_candidate_has_no_diagnosis_fields() -> None:
    fields = set(SpeciesCandidate.model_fields.keys())
    leaked = fields & FORBIDDEN_FIELDS
    assert not leaked, f"Forbidden diagnosis fields on SpeciesCandidate: {leaked}"


def test_species_candidate_field_types() -> None:
    hints = get_type_hints(SpeciesCandidate)
    assert hints["label_ko"] is str
    assert hints["label_en"] is str
    # scientific_name is Optional[str]
    assert str(hints["scientific_name"]) in {"str | None", "typing.Optional[str]"}
    assert hints["confidence"] is float
    assert hints["confidence_label"] is str
    assert hints["source"] is str
