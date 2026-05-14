"""LLM client factory — TICKET-049 / TICKET-055.

Returns a concrete LLMPort implementation based on settings.LLM_BACKEND.
Qwen client uses EndpointRegistry for dynamic RunPod endpoint resolution.
All imports are lazy so importing this module never triggers a provider connection.
"""

from __future__ import annotations

from app.llm.base import LLMPort


def get_llm_client() -> LLMPort:
    """Return the configured LLM client.

    ``mock``  → MockLLMClient (no network, deterministic responses)
    ``qwen``  → QwenLLMClient with EndpointRegistry (OpenAI-compatible vLLM)
    """
    from app.core.config import settings

    if settings.LLM_BACKEND == "qwen":
        from app.llm.endpoint_registry import EndpointRegistry
        from app.llm.qwen_client import QwenLLMClient

        session_factory = None
        if settings.QWEN_ENDPOINT_REGISTRY_MODE == "db":
            from app.db.session import AsyncSessionLocal

            session_factory = AsyncSessionLocal

        registry = EndpointRegistry(settings, session_factory=session_factory)

        return QwenLLMClient(
            endpoint_registry=registry,
            auth_header=settings.QWEN_LLM_AUTH_HEADER,
        )

    from app.llm.mock_client import MockLLMClient

    return MockLLMClient()
