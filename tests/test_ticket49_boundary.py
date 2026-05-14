"""TICKET-049 — boundary and invariant tests."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Isolation: orchestrator depends on LLMPort, not QwenLLMClient
# ---------------------------------------------------------------------------


def test_orchestrator_does_not_import_qwen_client() -> None:
    import app.services.chat_orchestrator as mod

    src = open(mod.__file__, encoding="utf-8").read()
    assert "QwenLLMClient" not in src
    assert "from app.llm.qwen_client" not in src
    assert "import qwen_client" not in src


def test_orchestrator_does_not_import_mock_client_directly() -> None:
    import app.services.chat_orchestrator as mod

    src = open(mod.__file__, encoding="utf-8").read()
    assert "MockLLMClient" not in src
    assert "from app.llm.mock_client import" not in src


def test_orchestrator_uses_client_factory() -> None:
    import app.services.chat_orchestrator as mod

    src = open(mod.__file__, encoding="utf-8").read()
    assert "get_llm_client" in src


# ---------------------------------------------------------------------------
# Isolation: qwen_client has no embedding or retrieval imports
# ---------------------------------------------------------------------------


def test_qwen_client_no_embedding_imports() -> None:
    import app.llm.qwen_client as mod

    src = open(mod.__file__, encoding="utf-8").read()
    for forbidden in ("LocalEmbeddingService", "EMBEDDING_MODEL_NAME", "HybridRetriever", "RetrievalService"):
        assert forbidden not in src, f"Forbidden in qwen_client: {forbidden!r}"


def test_qwen_client_no_prompt_builder() -> None:
    import app.llm.qwen_client as mod

    src = open(mod.__file__, encoding="utf-8").read()
    assert "PromptBuilder" not in src
    assert "EvidenceBuilder" not in src


# ---------------------------------------------------------------------------
# Config: LLM settings are separate from embedding settings
# ---------------------------------------------------------------------------


def test_llm_backend_config_exists() -> None:
    from app.core.config import settings

    assert hasattr(settings, "LLM_BACKEND")
    assert settings.LLM_BACKEND in ("mock", "qwen")


def test_qwen_llm_model_config_exists() -> None:
    from app.core.config import settings

    assert hasattr(settings, "QWEN_LLM_MODEL")
    assert settings.QWEN_LLM_MODEL != ""


def test_qwen_llm_base_url_config_exists() -> None:
    from app.core.config import settings

    assert hasattr(settings, "QWEN_LLM_BASE_URL")


def test_qwen_llm_timeout_config_exists() -> None:
    from app.core.config import settings

    assert hasattr(settings, "QWEN_LLM_TIMEOUT_SECONDS")
    assert settings.QWEN_LLM_TIMEOUT_SECONDS > 0


def test_embedding_config_separate_from_llm_config() -> None:
    from app.core.config import settings

    assert settings.EMBEDDING_MODEL_NAME != settings.QWEN_LLM_MODEL
    assert "Embedding" in settings.EMBEDDING_MODEL_NAME


# ---------------------------------------------------------------------------
# Factory: lazy imports do not trigger provider calls at startup
# ---------------------------------------------------------------------------


def test_importing_app_does_not_call_qwen() -> None:
    """Verify no network call happens during module imports."""
    from unittest.mock import patch

    with patch("httpx.AsyncClient") as mock_http:
        import importlib

        importlib.reload(importlib.import_module("app.services.chat_orchestrator"))

    mock_http.assert_not_called()


# ---------------------------------------------------------------------------
# base.py re-exports
# ---------------------------------------------------------------------------


def test_base_module_exports_llm_port() -> None:
    from app.llm.base import LLMPort

    assert LLMPort is not None


def test_base_module_exports_streaming_error() -> None:
    from app.llm.base import StreamingNotSupportedError

    assert issubclass(StreamingNotSupportedError, NotImplementedError)


# ---------------------------------------------------------------------------
# Mock client still works without network
# ---------------------------------------------------------------------------


def test_mock_client_has_no_httpx_import() -> None:
    import app.llm.mock_client as mod

    src = open(mod.__file__, encoding="utf-8").read()
    assert "import httpx" not in src
    assert "import requests" not in src
