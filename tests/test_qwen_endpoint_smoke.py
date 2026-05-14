"""TICKET-055 — smoke tests: file registry round-trip and client wiring."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_file_registry_round_trip(tmp_path: Path) -> None:
    """Write a JSON registry file, resolve via EndpointRegistry, verify values."""
    from app.llm.endpoint_registry import EndpointRegistry

    f = tmp_path / "qwen_endpoint.json"
    f.write_text(
        json.dumps({
            "provider": "qwen",
            "model": "qwen3.6",
            "base_url": "https://smoke-runpod.net",
            "api_key": None,
            "timeout_seconds": 60,
            "updated_at": "2026-05-14T12:00:00Z",
        }),
        encoding="utf-8",
    )

    from unittest.mock import MagicMock
    settings = MagicMock()
    settings.QWEN_ENDPOINT_REGISTRY_MODE = "file"
    settings.QWEN_ENDPOINT_REGISTRY_FILE = str(f)
    settings.QWEN_LLM_MODEL = "qwen3.6"
    settings.QWEN_LLM_TIMEOUT_SECONDS = 120.0
    settings.QWEN_LLM_API_KEY = ""

    reg = EndpointRegistry(settings)
    ep = await reg.resolve_qwen_endpoint()

    assert ep.base_url == "https://smoke-runpod.net"
    assert ep.model == "qwen3.6"
    assert ep.provider == "qwen"
    assert ep.source == "file"
    assert ep.api_key is None
    assert ep.timeout_seconds == 60.0


@pytest.mark.asyncio
async def test_qwen_client_with_registry_resolves_and_calls_endpoint(tmp_path: Path) -> None:
    """QwenLLMClient wired with a file registry calls the resolved endpoint."""
    import json as _json
    import uuid
    from unittest.mock import AsyncMock, MagicMock

    import httpx

    from app.llm.endpoint_registry import EndpointRegistry
    from app.llm.qwen_client import QwenLLMClient
    from app.services.llm_port import LLMRequest

    f = tmp_path / "qwen_endpoint.json"
    f.write_text(
        _json.dumps({
            "base_url": "https://smoke-runpod.net",
            "model": "qwen3.6",
            "timeout_seconds": 30,
        }),
        encoding="utf-8",
    )

    settings = MagicMock()
    settings.QWEN_ENDPOINT_REGISTRY_MODE = "file"
    settings.QWEN_ENDPOINT_REGISTRY_FILE = str(f)
    settings.QWEN_LLM_MODEL = "qwen3.6"
    settings.QWEN_LLM_TIMEOUT_SECONDS = 30.0
    settings.QWEN_LLM_API_KEY = ""

    registry = EndpointRegistry(settings)

    body = {
        "model": "qwen3.6",
        "choices": [{"message": {"content": "물주기 필요"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = body
    mock_resp.text = _json.dumps(body)

    http = AsyncMock(spec=httpx.AsyncClient)
    http.post = AsyncMock(return_value=mock_resp)

    client = QwenLLMClient(endpoint_registry=registry, http_client=http)

    req = LLMRequest(
        request_id=uuid.uuid4(),
        system_prompt="시스템",
        user_turn="물주기",
        prompt_hash="abc",
    )
    resp = await client.complete(req)

    assert resp.content == "물주기 필요"
    args, _ = http.post.call_args
    assert "smoke-runpod.net" in args[0]
