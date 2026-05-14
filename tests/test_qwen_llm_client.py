"""TICKET-049 — QwenLLMClient unit tests (mocked HTTP transport)."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.llm.qwen_client import LLMProviderError, QwenLLMClient
from app.services.llm_port import LLMRequest, LLMResponse, StreamingNotSupportedError


def _make_request(**kwargs) -> LLMRequest:
    defaults = {
        "request_id": uuid.uuid4(),
        "system_prompt": "식물 관리 AI입니다.",
        "user_turn": "물주기 알려줘",
        "prompt_hash": "abc123",
    }
    return LLMRequest(**{**defaults, **kwargs})


def _make_http_response(
    status_code: int = 200,
    model: str = "qwen3.6",
    content: str = "[결론] 물주기 필요\n\n[근거] 건조\n\n[행동] 주세요\n\n[주의] 과습 금지",
    finish_reason: str = "stop",
    prompt_tokens: int = 50,
    completion_tokens: int = 80,
) -> MagicMock:
    body = {
        "model": model,
        "choices": [
            {
                "message": {"content": content},
                "finish_reason": finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        },
    }
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = body
    resp.text = json.dumps(body)
    return resp


def _make_client(mock_resp: MagicMock) -> QwenLLMClient:
    http = AsyncMock(spec=httpx.AsyncClient)
    http.post = AsyncMock(return_value=mock_resp)
    return QwenLLMClient(
        base_url="http://localhost:8080",
        model="qwen3.6",
        timeout=10.0,
        http_client=http,
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_complete_returns_llm_response() -> None:
    client = _make_client(_make_http_response())
    resp = await client.complete(_make_request())
    assert isinstance(resp, LLMResponse)


@pytest.mark.asyncio
async def test_complete_echoes_request_id() -> None:
    rid = uuid.uuid4()
    client = _make_client(_make_http_response())
    resp = await client.complete(_make_request(request_id=rid))
    assert resp.request_id == rid


@pytest.mark.asyncio
async def test_complete_echoes_prompt_hash() -> None:
    client = _make_client(_make_http_response())
    req = _make_request(prompt_hash="deadzz99")
    resp = await client.complete(req)
    assert resp.prompt_hash == "deadzz99"


@pytest.mark.asyncio
async def test_complete_provider_is_qwen() -> None:
    client = _make_client(_make_http_response())
    resp = await client.complete(_make_request())
    assert resp.model_metadata.provider == "qwen"


@pytest.mark.asyncio
async def test_complete_model_name_from_response() -> None:
    client = _make_client(_make_http_response(model="qwen3.6-instruct"))
    resp = await client.complete(_make_request())
    assert resp.model_metadata.model_name == "qwen3.6-instruct"


@pytest.mark.asyncio
async def test_complete_tokens_mapped() -> None:
    client = _make_client(_make_http_response(prompt_tokens=120, completion_tokens=60))
    resp = await client.complete(_make_request())
    assert resp.input_tokens == 120
    assert resp.output_tokens == 60


@pytest.mark.asyncio
async def test_complete_finish_reason_stop() -> None:
    client = _make_client(_make_http_response(finish_reason="stop"))
    resp = await client.complete(_make_request())
    assert resp.finish_reason == "stop"


# ---------------------------------------------------------------------------
# Request body shape
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_body_contains_model() -> None:
    http = AsyncMock(spec=httpx.AsyncClient)
    http.post = AsyncMock(return_value=_make_http_response())
    client = QwenLLMClient("http://localhost:8080", "qwen3.6", 10.0, http_client=http)

    await client.complete(_make_request())

    _, kwargs = http.post.call_args
    body = kwargs["json"]
    assert body["model"] == "qwen3.6"


@pytest.mark.asyncio
async def test_request_body_contains_messages() -> None:
    http = AsyncMock(spec=httpx.AsyncClient)
    http.post = AsyncMock(return_value=_make_http_response())
    client = QwenLLMClient("http://localhost:8080", "qwen3.6", 10.0, http_client=http)

    req = _make_request(system_prompt="시스템", user_turn="유저 질문")
    await client.complete(req)

    _, kwargs = http.post.call_args
    messages = kwargs["json"]["messages"]
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "시스템"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "유저 질문"


@pytest.mark.asyncio
async def test_request_body_contains_max_tokens() -> None:
    http = AsyncMock(spec=httpx.AsyncClient)
    http.post = AsyncMock(return_value=_make_http_response())
    client = QwenLLMClient("http://localhost:8080", "qwen3.6", 10.0, http_client=http)

    await client.complete(_make_request(max_tokens=512))

    _, kwargs = http.post.call_args
    assert kwargs["json"]["max_tokens"] == 512


@pytest.mark.asyncio
async def test_request_body_stream_false() -> None:
    http = AsyncMock(spec=httpx.AsyncClient)
    http.post = AsyncMock(return_value=_make_http_response())
    client = QwenLLMClient("http://localhost:8080", "qwen3.6", 10.0, http_client=http)

    await client.complete(_make_request())

    _, kwargs = http.post.call_args
    assert kwargs["json"]["stream"] is False


@pytest.mark.asyncio
async def test_request_url_is_v1_chat_completions() -> None:
    http = AsyncMock(spec=httpx.AsyncClient)
    http.post = AsyncMock(return_value=_make_http_response())
    client = QwenLLMClient("http://localhost:8080", "qwen3.6", 10.0, http_client=http)

    await client.complete(_make_request())

    args, _ = http.post.call_args
    assert args[0].endswith("/v1/chat/completions")


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_timeout_raises_provider_error() -> None:
    http = AsyncMock(spec=httpx.AsyncClient)
    http.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
    client = QwenLLMClient("http://localhost:8080", "qwen3.6", 5.0, http_client=http)

    with pytest.raises(LLMProviderError, match="timed out"):
        await client.complete(_make_request())


@pytest.mark.asyncio
async def test_network_error_raises_provider_error() -> None:
    http = AsyncMock(spec=httpx.AsyncClient)
    http.post = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
    client = QwenLLMClient("http://localhost:8080", "qwen3.6", 5.0, http_client=http)

    with pytest.raises(LLMProviderError):
        await client.complete(_make_request())


@pytest.mark.asyncio
async def test_non_200_raises_provider_error() -> None:
    http = AsyncMock(spec=httpx.AsyncClient)
    err_resp = MagicMock(spec=httpx.Response)
    err_resp.status_code = 500
    err_resp.text = "Internal Server Error"
    http.post = AsyncMock(return_value=err_resp)
    client = QwenLLMClient("http://localhost:8080", "qwen3.6", 5.0, http_client=http)

    with pytest.raises(LLMProviderError, match="500"):
        await client.complete(_make_request())


@pytest.mark.asyncio
async def test_empty_choices_raises_provider_error() -> None:
    http = AsyncMock(spec=httpx.AsyncClient)
    empty_resp = MagicMock(spec=httpx.Response)
    empty_resp.status_code = 200
    empty_resp.json.return_value = {"choices": [], "usage": {}}
    http.post = AsyncMock(return_value=empty_resp)
    client = QwenLLMClient("http://localhost:8080", "qwen3.6", 5.0, http_client=http)

    with pytest.raises(LLMProviderError, match="empty"):
        await client.complete(_make_request())


@pytest.mark.asyncio
async def test_stream_true_raises_not_supported() -> None:
    client = QwenLLMClient("http://localhost:8080", "qwen3.6", 5.0)

    with pytest.raises(StreamingNotSupportedError):
        await client.complete(_make_request(stream=True))


# ---------------------------------------------------------------------------
# Isolation: embedding config never read
# ---------------------------------------------------------------------------


def test_qwen_client_does_not_import_embedding_config() -> None:
    import app.llm.qwen_client as mod

    src = open(mod.__file__, encoding="utf-8").read()
    assert "EMBEDDING_MODEL_NAME" not in src
    assert "EMBEDDING_VECTOR_DIM" not in src
    assert "LocalEmbeddingService" not in src


# ---------------------------------------------------------------------------
# Registry-based endpoint resolution (TICKET-055)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_client_calls_resolved_endpoint_not_constructor_url() -> None:
    """QwenLLMClient must use the registry URL, ignoring any static base_url."""
    from unittest.mock import AsyncMock as _AM

    from app.llm.endpoint_registry import LLMEndpoint

    mock_endpoint = LLMEndpoint(
        provider="qwen",
        model="qwen3.6",
        base_url="https://runpod-live.net",
        api_key=None,
        timeout_seconds=30.0,
        source="file",
    )
    mock_registry = _AM()
    mock_registry.resolve_qwen_endpoint.return_value = mock_endpoint

    http = AsyncMock(spec=httpx.AsyncClient)
    http.post = AsyncMock(return_value=_make_http_response())
    client = QwenLLMClient(
        base_url="http://stale-url:9999",  # must NOT be used
        model="qwen3.6",
        timeout=10.0,
        endpoint_registry=mock_registry,
        http_client=http,
    )

    await client.complete(_make_request())

    args, _ = http.post.call_args
    assert "runpod-live.net" in args[0]
    assert "stale-url" not in args[0]


@pytest.mark.asyncio
async def test_registry_resolved_per_request_enables_hot_swap() -> None:
    """A second call picks up the updated registry URL without restart."""
    from app.llm.endpoint_registry import LLMEndpoint

    endpoint_v1 = LLMEndpoint(
        provider="qwen", model="qwen3.6",
        base_url="https://runpod-v1.net", api_key=None,
        timeout_seconds=30.0, source="file",
    )
    endpoint_v2 = LLMEndpoint(
        provider="qwen", model="qwen3.6",
        base_url="https://runpod-v2.net", api_key=None,
        timeout_seconds=30.0, source="file",
    )

    call_count = 0

    async def _resolve():
        nonlocal call_count
        call_count += 1
        return endpoint_v1 if call_count == 1 else endpoint_v2

    mock_registry = MagicMock()
    mock_registry.resolve_qwen_endpoint = _resolve

    http = AsyncMock(spec=httpx.AsyncClient)
    http.post = AsyncMock(return_value=_make_http_response())
    client = QwenLLMClient(endpoint_registry=mock_registry, http_client=http)

    await client.complete(_make_request())
    await client.complete(_make_request())

    urls = [call[0][0] for call in http.post.call_args_list]
    assert "runpod-v1.net" in urls[0]
    assert "runpod-v2.net" in urls[1]


@pytest.mark.asyncio
async def test_authorization_header_sent_when_api_key_set() -> None:
    from app.llm.endpoint_registry import LLMEndpoint

    mock_endpoint = LLMEndpoint(
        provider="qwen", model="qwen3.6",
        base_url="https://runpod.net", api_key="my-secret-key",
        timeout_seconds=30.0, source="env",
    )
    mock_registry = MagicMock()
    mock_registry.resolve_qwen_endpoint = AsyncMock(return_value=mock_endpoint)

    http = AsyncMock(spec=httpx.AsyncClient)
    http.post = AsyncMock(return_value=_make_http_response())
    client = QwenLLMClient(endpoint_registry=mock_registry, http_client=http)

    await client.complete(_make_request())

    _, kwargs = http.post.call_args
    headers = kwargs.get("headers") or {}
    assert "Authorization" in headers
    assert headers["Authorization"] == "Bearer my-secret-key"


@pytest.mark.asyncio
async def test_no_auth_header_when_api_key_absent() -> None:
    from app.llm.endpoint_registry import LLMEndpoint

    mock_endpoint = LLMEndpoint(
        provider="qwen", model="qwen3.6",
        base_url="https://runpod.net", api_key=None,
        timeout_seconds=30.0, source="env",
    )
    mock_registry = MagicMock()
    mock_registry.resolve_qwen_endpoint = AsyncMock(return_value=mock_endpoint)

    http = AsyncMock(spec=httpx.AsyncClient)
    http.post = AsyncMock(return_value=_make_http_response())
    client = QwenLLMClient(endpoint_registry=mock_registry, http_client=http)

    await client.complete(_make_request())

    _, kwargs = http.post.call_args
    headers = kwargs.get("headers") or {}
    assert "Authorization" not in headers
