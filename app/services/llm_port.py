"""LLMPort — TICKET-017.

Provider-neutral protocol for LLM completion.  Any real client (Anthropic,
OpenAI, local Ollama …) or a mock must implement `LLMPort`.

Streaming is explicitly out-of-scope for this ticket; callers that request
it receive a `StreamingNotSupportedError`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class StreamingNotSupportedError(NotImplementedError):
    """Raised when a caller requests streaming, which is not yet supported."""


# ---------------------------------------------------------------------------
# Request / Response
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LLMRequest:
    request_id: uuid.UUID
    system_prompt: str          # Full system context (from PromptBuilder)
    user_turn: str              # Verbatim user question
    prompt_hash: str            # SHA-256 of system_prompt; used for caching
    max_tokens: int = 1024
    temperature: float = 0.0   # 0.0 → maximally deterministic
    stream: bool = False        # Must be False; True raises StreamingNotSupportedError


@dataclass(frozen=True)
class ModelMetadata:
    model_name: str
    provider: str
    api_version: str = "n/a"


@dataclass(frozen=True)
class LLMResponse:
    request_id: uuid.UUID
    content: str                # The generated text (must include all 4 sections)
    prompt_hash: str            # Echoed from LLMRequest
    model_metadata: ModelMetadata
    input_tokens: int
    output_tokens: int
    finish_reason: str          # "stop" | "length" | "error"


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class LLMPort(Protocol):
    """Structural protocol every LLM client must satisfy."""

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Send *request* and return the completion.

        Raises `StreamingNotSupportedError` if request.stream is True.
        Must never make network calls for mock implementations.
        """
        ...
