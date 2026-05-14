"""QwenLLMClient — TICKET-049.

Adapter for Qwen3.6 served behind an OpenAI-compatible HTTP API (e.g. vLLM).
No embedding logic, no retrieval logic, no prompt building.

Raises `LLMProviderError` on network failure, timeout, or non-2xx response.
The caller (ChatOrchestrator) depends on LLMPort; this file is never imported
directly by the orchestrator.
"""

from __future__ import annotations

import httpx

from app.llm.base import (
    LLMPort,
    LLMRequest,
    LLMResponse,
    ModelMetadata,
    StreamingNotSupportedError,
)


class LLMProviderError(RuntimeError):
    """Raised when the LLM provider returns an error or is unreachable."""


_PROVIDER = "qwen"
_API_VERSION = "vllm"


class QwenLLMClient:
    """LLMPort implementation backed by a Qwen vLLM OpenAI-compatible endpoint."""

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: float,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._http_client = http_client  # injectable for unit tests

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if request.stream:
            raise StreamingNotSupportedError(
                "QwenLLMClient does not support streaming."
            )

        payload: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_turn},
            ],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": False,
        }

        url = f"{self._base_url}/v1/chat/completions"

        try:
            resp = await self._post(url, payload)
        except httpx.TimeoutException as exc:
            raise LLMProviderError(
                f"Qwen request timed out after {self._timeout}s: {exc}"
            ) from exc
        except httpx.RequestError as exc:
            raise LLMProviderError(f"Qwen network error: {exc}") from exc

        if resp.status_code != 200:
            raise LLMProviderError(
                f"Qwen provider returned HTTP {resp.status_code}: {resp.text[:300]}"
            )

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            raise LLMProviderError("Qwen provider returned an empty choices list.")

        choice = choices[0]
        content: str = choice["message"]["content"]
        finish_reason: str = choice.get("finish_reason") or "stop"
        usage: dict = data.get("usage", {})

        return LLMResponse(
            request_id=request.request_id,
            content=content,
            prompt_hash=request.prompt_hash,
            model_metadata=ModelMetadata(
                model_name=data.get("model", self._model),
                provider=_PROVIDER,
                api_version=_API_VERSION,
            ),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            finish_reason=finish_reason,
        )

    async def _post(self, url: str, payload: dict) -> httpx.Response:
        if self._http_client is not None:
            return await self._http_client.post(url, json=payload)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            return await client.post(url, json=payload)


# Structural conformance check — verified at import time, not at runtime.
def _assert_implements_port() -> None:
    assert isinstance(
        QwenLLMClient("http://localhost", "qwen3.6", 30.0),
        LLMPort,
    ), "QwenLLMClient must satisfy LLMPort"
