"""LLM client factory — TICKET-049.

Returns a concrete LLMPort implementation based on settings.LLM_BACKEND.
The Qwen client is imported lazily so importing this module never triggers
a provider connection.
"""

from __future__ import annotations

from app.llm.base import LLMPort


def get_llm_client() -> LLMPort:
    """Return the configured LLM client.

    ``mock``  → MockLLMClient (no network, deterministic responses)
    ``qwen``  → QwenLLMClient (OpenAI-compatible HTTP to vLLM)
    """
    from app.core.config import settings

    if settings.LLM_BACKEND == "qwen":
        from app.llm.qwen_client import QwenLLMClient

        return QwenLLMClient(
            base_url=settings.QWEN_LLM_BASE_URL,
            model=settings.QWEN_LLM_MODEL,
            timeout=settings.QWEN_LLM_TIMEOUT_SECONDS,
        )

    from app.llm.mock_client import MockLLMClient

    return MockLLMClient()
