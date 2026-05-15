"""TICKET-060A3 — MockSpeciesClassifier behavior tests.

Verifies catalog-aligned deterministic output, top_k, and confirms
no file/network/model side-effects occur during classification.
"""

import asyncio
import builtins
import socket

import pytest

from app.vision.mock_species_classifier import MockSpeciesClassifier


def _classify(image_ref: str, **kwargs):
    classifier = MockSpeciesClassifier()
    return asyncio.run(classifier.classify_species(image_ref, **kwargs))


# ---------------------------------------------------------------------------
# Any image_ref returns catalog candidates (no keyword matching)
# ---------------------------------------------------------------------------


def test_any_image_ref_returns_candidates() -> None:
    result = _classify("uploads/mock/monstera.jpg")
    assert len(result) >= 1
    assert result[0].label_ko == "몬스테라 델리시오사"


def test_uuid_image_ref_returns_candidates() -> None:
    result = _classify("4aa78846-cf8c-4d2b-87cb-365e9e64a2cc.jpg")
    assert len(result) >= 1
    assert result[0].scientific_name == "Monstera deliciosa"


def test_empty_image_ref_returns_candidates() -> None:
    result = _classify("")
    assert len(result) >= 1
    assert result[0].label_ko == "몬스테라 델리시오사"


def test_unknown_image_ref_returns_catalog_candidates_not_fallback() -> None:
    result = _classify("uploads/mock/unrecognized-plant.jpg")
    assert result[0].label_ko != "잘 모르겠어요"
    assert result[0].scientific_name is not None


# ---------------------------------------------------------------------------
# Candidate values
# ---------------------------------------------------------------------------


def test_first_candidate_is_monstera() -> None:
    result = _classify("any-ref")
    assert result[0].label_ko == "몬스테라 델리시오사"
    assert result[0].label_en == "Monstera"
    assert result[0].scientific_name == "Monstera deliciosa"
    assert result[0].confidence == 0.60
    assert result[0].confidence_label == "medium"
    assert result[0].source == "catalog_mock"


def test_second_candidate_is_skinnapseoseu() -> None:
    result = _classify("any-ref", top_k=3)
    assert result[1].label_ko == "스킨답서스"
    assert result[1].scientific_name == "Epipremnum aureum"
    assert result[1].confidence == 0.50
    assert result[1].confidence_label == "medium"
    assert result[1].source == "catalog_mock"


def test_third_candidate_is_spathiphyllum() -> None:
    result = _classify("any-ref", top_k=3)
    assert result[2].label_ko == "스파티필름"
    assert result[2].scientific_name == "Spathiphyllum wallisii"
    assert result[2].confidence == 0.45
    assert result[2].confidence_label == "low"
    assert result[2].source == "catalog_mock"


# ---------------------------------------------------------------------------
# top_k
# ---------------------------------------------------------------------------


def test_top_k_one_returns_single_candidate() -> None:
    result = _classify("any-ref", top_k=1)
    assert len(result) == 1
    assert result[0].label_ko == "몬스테라 델리시오사"


def test_top_k_two_returns_two_candidates() -> None:
    result = _classify("any-ref", top_k=2)
    assert len(result) == 2


def test_top_k_three_returns_three_candidates() -> None:
    result = _classify("any-ref", top_k=3)
    assert len(result) == 3


def test_top_k_zero_returns_at_least_one() -> None:
    result = _classify("any-ref", top_k=0)
    assert len(result) >= 1


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_same_image_ref_returns_same_output() -> None:
    a = _classify("uploads/mock/monstera.jpg")
    b = _classify("uploads/mock/monstera.jpg")
    assert [c.model_dump() for c in a] == [c.model_dump() for c in b]


def test_different_image_refs_return_same_output() -> None:
    a = _classify("any-uuid-ref.jpg")
    b = _classify("uploads/mock/pothos.jpg")
    assert [c.model_dump() for c in a] == [c.model_dump() for c in b]


# ---------------------------------------------------------------------------
# No file / network / model side-effects during classification
# ---------------------------------------------------------------------------


def test_classify_does_not_open_files(monkeypatch) -> None:
    real_open = builtins.open
    calls: list[str] = []

    def fake_open(*args, **kwargs):
        calls.append(str(args[0]) if args else "<no-arg>")
        return real_open(*args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)
    _classify("uploads/mock/monstera.jpg")
    assert not any("monstera" in c for c in calls), f"open() touched image_ref: {calls}"


def test_classify_does_not_open_socket(monkeypatch) -> None:
    real_socket = socket.socket
    counter = {"n": 0}

    def counting_socket(*args, **kwargs):
        counter["n"] += 1
        return real_socket(*args, **kwargs)

    classifier = MockSpeciesClassifier()

    async def _go() -> int:
        before = counter["n"]
        await classifier.classify_species("uploads/mock/monstera.jpg")
        return counter["n"] - before

    monkeypatch.setattr(socket, "socket", counting_socket)
    delta = asyncio.run(_go())
    assert delta == 0, f"classify_species opened {delta} socket(s)"


def test_classify_does_not_import_heavy_libs() -> None:
    import sys

    classifier = MockSpeciesClassifier()
    asyncio.run(classifier.classify_species("uploads/mock/monstera.jpg"))
    forbidden = {
        "torch",
        "torchvision",
        "tensorflow",
        "cv2",
        "PIL",
        "onnxruntime",
        "openvino",
        "transformers",
        "ultralytics",
    }
    leaked = forbidden & set(sys.modules.keys())
    assert not leaked, f"Forbidden libs imported: {leaked}"


# ---------------------------------------------------------------------------
# No diagnosis / disease / pest fields leak
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "image_ref",
    [
        "uploads/mock/monstera.jpg",
        "4aa78846-cf8c-4d2b-87cb-365e9e64a2cc.jpg",
        "uploads/mock/foo.jpg",
        "",
    ],
)
def test_no_diagnosis_fields(image_ref: str) -> None:
    result = _classify(image_ref)
    forbidden = {
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
    for c in result:
        leaked = set(c.model_dump().keys()) & forbidden
        assert not leaked, f"Forbidden field on candidate: {leaked}"
