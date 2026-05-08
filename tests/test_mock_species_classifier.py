"""TICKET-003 — MockSpeciesClassifier behavior tests.

Verifies deterministic keyword matching, fallback behavior, and confirms
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
# Keyword matching — known species
# ---------------------------------------------------------------------------


def test_monstera_english_keyword() -> None:
    result = _classify("uploads/mock/monstera.jpg")
    assert result[0].label_ko == "몬스테라"
    assert result[0].label_en == "Monstera"
    assert result[0].scientific_name == "Monstera deliciosa"
    assert result[0].confidence == 0.91
    assert result[0].confidence_label == "high"
    assert result[0].source == "mock"


def test_monstera_korean_keyword() -> None:
    result = _classify("uploads/mock/몬스테라.jpg")
    assert result[0].label_ko == "몬스테라"
    assert result[0].scientific_name == "Monstera deliciosa"


def test_pothos_english_keyword() -> None:
    result = _classify("uploads/mock/pothos.jpg")
    assert result[0].label_ko == "스킨답서스"
    assert result[0].label_en == "Pothos"
    assert result[0].scientific_name == "Epipremnum aureum"
    assert result[0].confidence == 0.88


def test_pothos_korean_keyword() -> None:
    result = _classify("uploads/mock/스킨답서스.jpg")
    assert result[0].label_ko == "스킨답서스"


def test_philodendron_english_keyword() -> None:
    result = _classify("uploads/mock/philodendron.jpg")
    assert result[0].label_ko == "필로덴드론"
    assert result[0].label_en == "Philodendron"
    assert result[0].scientific_name == "Philodendron hederaceum"
    assert result[0].confidence == 0.84
    assert result[0].confidence_label == "medium"


def test_philodendron_korean_keyword() -> None:
    result = _classify("uploads/mock/필로덴드론.jpg")
    assert result[0].label_ko == "필로덴드론"


# ---------------------------------------------------------------------------
# Fallback / unknown
# ---------------------------------------------------------------------------


def test_unknown_image_ref_returns_fallback() -> None:
    result = _classify("uploads/mock/unrecognized-plant.jpg")
    assert result[0].label_ko == "잘 모르겠어요"
    assert result[0].label_en == "Unknown"
    assert result[0].scientific_name is None
    assert result[0].confidence == 0.0
    assert result[0].confidence_label == "low"
    assert result[0].source == "mock"


def test_empty_image_ref_returns_fallback() -> None:
    result = _classify("")
    assert result[0].label_ko == "잘 모르겠어요"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_same_image_ref_returns_same_output() -> None:
    a = _classify("uploads/mock/monstera.jpg")
    b = _classify("uploads/mock/monstera.jpg")
    assert [c.model_dump() for c in a] == [c.model_dump() for c in b]


def test_unknown_same_input_same_output() -> None:
    a = _classify("uploads/mock/foo.jpg")
    b = _classify("uploads/mock/foo.jpg")
    assert [c.model_dump() for c in a] == [c.model_dump() for c in b]


# ---------------------------------------------------------------------------
# top_k
# ---------------------------------------------------------------------------


def test_top_k_one_returns_single_candidate() -> None:
    result = _classify("uploads/mock/monstera.jpg", top_k=1)
    assert len(result) == 1
    assert result[0].label_ko == "몬스테라"


def test_top_k_three_returns_up_to_three_for_known() -> None:
    result = _classify("uploads/mock/monstera.jpg", top_k=3)
    assert 1 <= len(result) <= 3
    assert result[0].label_ko == "몬스테라"


def test_top_k_one_for_unknown_returns_fallback_only() -> None:
    result = _classify("uploads/mock/foo.jpg", top_k=1)
    assert len(result) == 1
    assert result[0].label_ko == "잘 모르겠어요"


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
    # The classifier itself must never call open() during classification.
    # (Other test machinery may, but we assert classify produced no extra open calls
    # specifically referencing the image_ref path.)
    assert not any("monstera" in c for c in calls), f"open() touched image_ref: {calls}"


def test_classify_does_not_open_socket(monkeypatch) -> None:
    # Spy on socket.socket: count calls strictly during classify_species.
    # The asyncio runtime itself opens a socketpair when constructing a new
    # event loop, so we measure the delta around the awaited call.
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
    """Heavy ML / image libraries must not be importable side-effects of classify."""
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
        "uploads/mock/pothos.jpg",
        "uploads/mock/philodendron.jpg",
        "uploads/mock/foo.jpg",
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
