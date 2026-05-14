"""TICKET-049 — LLMPort structural contract tests."""

from __future__ import annotations

import inspect

from app.services.llm_port import LLMPort


def test_qwen_client_satisfies_llm_port() -> None:
    from app.llm.qwen_client import QwenLLMClient

    client = QwenLLMClient("http://localhost:8080", "qwen3.6", 30.0)
    assert isinstance(client, LLMPort)


def test_qwen_client_has_complete_method() -> None:
    from app.llm.qwen_client import QwenLLMClient

    assert hasattr(QwenLLMClient, "complete")
    assert inspect.iscoroutinefunction(QwenLLMClient.complete)


def test_mock_client_still_satisfies_llm_port() -> None:
    from app.llm.mock_client import MockLLMClient

    client = MockLLMClient()
    assert isinstance(client, LLMPort)


def test_qwen_provider_is_qwen() -> None:
    from app.llm.qwen_client import _PROVIDER

    assert _PROVIDER == "qwen"


def test_llm_provider_error_is_runtime_error() -> None:
    from app.llm.qwen_client import LLMProviderError

    err = LLMProviderError("test")
    assert isinstance(err, RuntimeError)
