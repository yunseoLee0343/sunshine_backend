"""TICKET-060A5 — Species classifier provider factory tests."""

import pytest

from app.vision.mock_species_classifier import MockSpeciesClassifier
from app.vision.plant_id_species_classifier import PlantIdSpeciesClassifier
from app.vision.qwen_vl_species_classifier import QwenVLSpeciesClassifier


# ---------------------------------------------------------------------------
# QwenVLSpeciesClassifier construction
# ---------------------------------------------------------------------------


def test_qwen_vl_classifier_requires_base_url() -> None:
    with pytest.raises(ValueError, match="QWEN_VL_BASE_URL"):
        QwenVLSpeciesClassifier(base_url="")


def test_qwen_vl_classifier_accepts_valid_base_url() -> None:
    clf = QwenVLSpeciesClassifier(base_url="http://localhost:8080")
    assert clf._base_url == "http://localhost:8080"


def test_qwen_vl_classifier_strips_trailing_slash() -> None:
    clf = QwenVLSpeciesClassifier(base_url="http://localhost:8080/")
    assert clf._base_url == "http://localhost:8080"


def test_qwen_vl_classify_species_raises_not_implemented() -> None:
    import asyncio
    clf = QwenVLSpeciesClassifier(base_url="http://localhost:8080")
    with pytest.raises(NotImplementedError):
        asyncio.run(clf.classify_species("any-ref"))


# ---------------------------------------------------------------------------
# No import-time network side-effects
# ---------------------------------------------------------------------------


def test_qwen_vl_import_does_not_open_socket(monkeypatch) -> None:
    import socket
    counter = {"n": 0}
    real_socket = socket.socket

    def counting_socket(*args, **kwargs):
        counter["n"] += 1
        return real_socket(*args, **kwargs)

    monkeypatch.setattr(socket, "socket", counting_socket)
    # Constructing the classifier (without calling classify_species) must not
    # open any sockets.
    QwenVLSpeciesClassifier(base_url="http://localhost:8080")
    assert counter["n"] == 0


# ---------------------------------------------------------------------------
# get_species_classifier() factory routing
# ---------------------------------------------------------------------------


def _get_classifier(provider: str):
    from unittest.mock import patch
    from app.api import plants as plants_mod
    plants_mod._plant_id_classifier = None
    plants_mod._qwen_vl_classifier = None
    with patch.object(plants_mod.settings, "SPECIES_CLASSIFIER_PROVIDER", provider):
        return plants_mod.get_species_classifier()


def test_factory_catalog_mock_returns_mock_classifier() -> None:
    clf = _get_classifier("catalog_mock")
    assert isinstance(clf, MockSpeciesClassifier)


def test_factory_mock_alias_returns_mock_classifier() -> None:
    clf = _get_classifier("mock")
    assert isinstance(clf, MockSpeciesClassifier)


def test_factory_plant_id_returns_plant_id_classifier() -> None:
    clf = _get_classifier("plant_id")
    assert isinstance(clf, PlantIdSpeciesClassifier)


def test_factory_qwen_vl_raises_without_base_url() -> None:
    from unittest.mock import patch
    from app.api import plants as plants_mod
    plants_mod._qwen_vl_classifier = None
    with patch.object(plants_mod.settings, "SPECIES_CLASSIFIER_PROVIDER", "qwen_vl"):
        with patch.object(plants_mod.settings, "QWEN_VL_BASE_URL", ""):
            with pytest.raises(ValueError, match="QWEN_VL_BASE_URL"):
                plants_mod.get_species_classifier()


def test_factory_qwen_vl_returns_qwen_vl_classifier() -> None:
    from unittest.mock import patch
    from app.api import plants as plants_mod
    plants_mod._qwen_vl_classifier = None
    with patch.object(plants_mod.settings, "SPECIES_CLASSIFIER_PROVIDER", "qwen_vl"):
        with patch.object(plants_mod.settings, "QWEN_VL_BASE_URL", "http://vllm:8080"):
            clf = plants_mod.get_species_classifier()
    assert isinstance(clf, QwenVLSpeciesClassifier)


def test_factory_unknown_provider_raises_runtime_error() -> None:
    from app.api import plants as plants_mod
    with pytest.raises(RuntimeError, match="unsupported"):
        _get_classifier("unknown_provider")
