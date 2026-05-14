"""TICKET-049 — LLM client factory tests."""

from __future__ import annotations

from unittest.mock import patch


def test_factory_returns_mock_when_backend_mock() -> None:
    from app.llm.client_factory import get_llm_client
    from app.llm.mock_client import MockLLMClient

    with patch("app.core.config.settings") as mock_settings:
        mock_settings.LLM_BACKEND = "mock"
        client = get_llm_client()

    assert isinstance(client, MockLLMClient)


def test_factory_returns_qwen_when_backend_qwen() -> None:
    from app.llm.client_factory import get_llm_client
    from app.llm.qwen_client import QwenLLMClient

    with patch("app.core.config.settings") as mock_settings:
        mock_settings.LLM_BACKEND = "qwen"
        mock_settings.QWEN_LLM_BASE_URL = "http://localhost:8080"
        mock_settings.QWEN_LLM_MODEL = "qwen3.6"
        mock_settings.QWEN_LLM_TIMEOUT_SECONDS = 30.0
        mock_settings.QWEN_ENDPOINT_REGISTRY_MODE = "env"
        mock_settings.QWEN_LLM_AUTH_HEADER = "Authorization"
        client = get_llm_client()

    assert isinstance(client, QwenLLMClient)


def test_factory_default_is_mock() -> None:
    from app.core.config import settings
    from app.llm.client_factory import get_llm_client
    from app.llm.mock_client import MockLLMClient

    assert settings.LLM_BACKEND == "mock"
    client = get_llm_client()
    assert isinstance(client, MockLLMClient)


def test_factory_qwen_client_uses_endpoint_registry() -> None:
    """Factory wires up an EndpointRegistry; resolution deferred to request time."""
    from app.llm.client_factory import get_llm_client
    from app.llm.endpoint_registry import EndpointRegistry
    from app.llm.qwen_client import QwenLLMClient

    with patch("app.core.config.settings") as mock_settings:
        mock_settings.LLM_BACKEND = "qwen"
        mock_settings.QWEN_LLM_BASE_URL = "http://my-vllm:9000"
        mock_settings.QWEN_LLM_MODEL = "qwen3.6"
        mock_settings.QWEN_LLM_TIMEOUT_SECONDS = 15.0
        mock_settings.QWEN_ENDPOINT_REGISTRY_MODE = "env"
        mock_settings.QWEN_LLM_AUTH_HEADER = "Authorization"
        client = get_llm_client()

    assert isinstance(client, QwenLLMClient)
    assert isinstance(client._endpoint_registry, EndpointRegistry)


def test_factory_does_not_call_provider_at_import() -> None:
    """Importing the factory must not trigger a network call."""
    import importlib

    with patch("httpx.AsyncClient") as mock_http:
        importlib.import_module("app.llm.client_factory")

    mock_http.assert_not_called()
