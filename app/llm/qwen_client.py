"""QwenLLMClient — TICKET-049 / TICKET-055.

Adapter for Qwen3.6 served behind an OpenAI-compatible HTTP API (e.g. vLLM).
Supports dynamic endpoint resolution via EndpointRegistry (TICKET-055) as well
as the original static base_url constructor for backward compatibility.

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
    """LLMPort implementation backed by a Qwen vLLM OpenAI-compatible endpoint.

    Accepts either a static base_url (original TICKET-049 API) or an
    EndpointRegistry that resolves the current RunPod endpoint per-request.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        *,
        endpoint_registry=None,
        api_key: str | None = None,
        auth_header: str = "Authorization",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/") if base_url else None
        self._model = model
        self._timeout = timeout
        self._endpoint_registry = endpoint_registry
        self._api_key = api_key
        self._auth_header = auth_header
        self._http_client = http_client  # injectable for unit tests

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if request.stream:
            raise StreamingNotSupportedError(
                "QwenLLMClient does not support streaming."
            )

        # Resolve endpoint — dynamic (registry) or static (constructor).
        if self._endpoint_registry is not None:
            ep = await self._endpoint_registry.resolve_qwen_endpoint()
            base_url = ep.base_url
            model = ep.model
            timeout = ep.timeout_seconds
            api_key = ep.api_key if ep.api_key is not None else self._api_key
        else:
            base_url = self._base_url
            model = self._model
            timeout = self._timeout
            api_key = self._api_key

        headers: dict[str, str] = {}
        if api_key:
            headers[self._auth_header] = f"Bearer {api_key}"

        payload: dict = {
            "model": model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_turn},
            ],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": False,
        }

        url = f"{base_url}/v1/chat/completions"

        try:
            resp = await self._post(url, payload, headers=headers, timeout=timeout)
        except httpx.TimeoutException as exc:
            raise LLMProviderError(
                f"Qwen request timed out after {timeout}s: {exc}"
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
                model_name=data.get("model", model),
                provider=_PROVIDER,
                api_version=_API_VERSION,
            ),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            finish_reason=finish_reason,
        )

    async def _post(
        self,
        url: str,
        payload: dict,
        *,
        headers: dict | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        if self._http_client is not None:
            return await self._http_client.post(url, json=payload, headers=headers)
        effective_timeout = timeout if timeout is not None else self._timeout
        async with httpx.AsyncClient(timeout=effective_timeout) as client:
            return await client.post(url, json=payload, headers=headers)


# Structural conformance check — verified at import time, not at runtime.
def _assert_implements_port() -> None:
    assert isinstance(
        QwenLLMClient("http://localhost", "qwen3.6", 30.0),
        LLMPort,
    ), "QwenLLMClient must satisfy LLMPort"
