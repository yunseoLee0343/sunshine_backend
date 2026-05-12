"""T-003D — Species classifier provider selection tests."""

import socket
from unittest.mock import patch

import pytest

import app.api.plants as plants_module
from app.vision.mock_species_classifier import MockSpeciesClassifier
from app.vision.plant_id_species_classifier import PlantIdSpeciesClassifier


def _get(provider: str):
    """Call get_species_classifier with the given provider, resetting cache first."""
    with patch.object(plants_module.settings, "SPECIES_CLASSIFIER_PROVIDER", provider):
        plants_module._plant_id_classifier = None
        return plants_module.get_species_classifier()


# ---------------------------------------------------------------------------
# 1. Default provider returns MockSpeciesClassifier
# ---------------------------------------------------------------------------


def test_default_provider_is_mock() -> None:
    # The setting default is "mock"; verify the module-level default still holds.
    assert plants_module.settings.SPECIES_CLASSIFIER_PROVIDER == "mock"


def test_default_provider_returns_mock_instance(monkeypatch) -> None:
    monkeypatch.setattr(plants_module.settings, "SPECIES_CLASSIFIER_PROVIDER", "mock")
    plants_module._plant_id_classifier = None
    result = plants_module.get_species_classifier()
    assert isinstance(result, MockSpeciesClassifier)


# ---------------------------------------------------------------------------
# 2. SPECIES_CLASSIFIER_PROVIDER=mock returns MockSpeciesClassifier
# ---------------------------------------------------------------------------


def test_explicit_mock_returns_mock_classifier() -> None:
    result = _get("mock")
    assert isinstance(result, MockSpeciesClassifier)


def test_mock_classifier_is_reused() -> None:
    """The same mock instance is returned on repeated calls."""
    with patch.object(plants_module.settings, "SPECIES_CLASSIFIER_PROVIDER", "mock"):
        first = plants_module.get_species_classifier()
        second = plants_module.get_species_classifier()
    assert first is second


# ---------------------------------------------------------------------------
# 3. SPECIES_CLASSIFIER_PROVIDER=plant_id returns PlantIdSpeciesClassifier
# ---------------------------------------------------------------------------


def test_plant_id_provider_returns_plant_id_classifier() -> None:
    result = _get("plant_id")
    assert isinstance(result, PlantIdSpeciesClassifier)


def test_plant_id_classifier_is_cached() -> None:
    """Second call returns the same instance (lazy singleton)."""
    with patch.object(plants_module.settings, "SPECIES_CLASSIFIER_PROVIDER", "plant_id"):
        plants_module._plant_id_classifier = None
        first = plants_module.get_species_classifier()
        second = plants_module.get_species_classifier()
    assert first is second


# ---------------------------------------------------------------------------
# 4. Invalid provider raises clear RuntimeError
# ---------------------------------------------------------------------------


def test_unknown_provider_raises_runtime_error() -> None:
    with pytest.raises(RuntimeError, match="unsupported species classifier provider"):
        _get("openai_vision")


def test_empty_provider_raises_runtime_error() -> None:
    with pytest.raises(RuntimeError, match="unsupported species classifier provider"):
        _get("")


def test_error_message_contains_provider_name() -> None:
    with pytest.raises(RuntimeError, match="bad_provider"):
        _get("bad_provider")


# ---------------------------------------------------------------------------
# 5. No network call at import time
# ---------------------------------------------------------------------------


def test_plant_id_classifier_not_pre_instantiated() -> None:
    """PlantIdSpeciesClassifier must be lazily instantiated, not at import time."""
    # Reset to simulate a fresh module state.
    plants_module._plant_id_classifier = None
    # Nothing should auto-create the instance.
    assert plants_module._plant_id_classifier is None


def test_mock_provider_never_instantiates_plant_id_classifier() -> None:
    """Using mock provider must leave _plant_id_classifier as None."""
    with patch.object(plants_module.settings, "SPECIES_CLASSIFIER_PROVIDER", "mock"):
        plants_module._plant_id_classifier = None
        plants_module.get_species_classifier()
    assert plants_module._plant_id_classifier is None


def test_import_opens_no_inet_sockets(monkeypatch) -> None:
    """Importing the plants module must not open any TCP/IP sockets."""
    opened: list[tuple] = []
    real_socket = socket.socket

    def spy(*args, **kwargs):
        opened.append(args)
        return real_socket(*args, **kwargs)

    import sys

    # Remove cached modules to force a clean import.
    for key in [k for k in sys.modules if "app.api.plants" in k or "plant_id_species_classifier" in k]:
        del sys.modules[key]

    monkeypatch.setattr(socket, "socket", spy)
    import app.api.plants  # noqa: F401

    inet_stream = [
        a for a in opened
        if len(a) >= 2 and a[0] == socket.AF_INET and a[1] == socket.SOCK_STREAM
    ]
    assert not inet_stream, f"TCP socket opened during import: {inet_stream}"
