"""TICKET-055 — EndpointRegistry unit tests (no network calls)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.endpoint_registry import EndpointRegistry


def _settings(
    mode: str = "env",
    base_url: str = "http://localhost:8080",
    model: str = "qwen3.6",
    timeout: float = 120.0,
    api_key: str = "",
    auth_header: str = "Authorization",
    registry_file: str = "/app/runtime/qwen_endpoint.json",
):
    s = MagicMock()
    s.QWEN_ENDPOINT_REGISTRY_MODE = mode
    s.QWEN_LLM_BASE_URL = base_url
    s.QWEN_LLM_MODEL = model
    s.QWEN_LLM_TIMEOUT_SECONDS = timeout
    s.QWEN_LLM_API_KEY = api_key
    s.QWEN_ENDPOINT_REGISTRY_FILE = registry_file
    return s


# ---------------------------------------------------------------------------
# Env mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_env_mode_returns_static_url() -> None:
    reg = EndpointRegistry(_settings(mode="env", base_url="http://vllm.local:8000"))
    ep = await reg.resolve_qwen_endpoint()
    assert ep.base_url == "http://vllm.local:8000"
    assert ep.source == "env"


@pytest.mark.asyncio
async def test_env_mode_strips_trailing_slash() -> None:
    reg = EndpointRegistry(_settings(mode="env", base_url="http://vllm.local:8000/"))
    ep = await reg.resolve_qwen_endpoint()
    assert ep.base_url == "http://vllm.local:8000"


@pytest.mark.asyncio
async def test_env_mode_api_key_empty_string_becomes_none() -> None:
    reg = EndpointRegistry(_settings(mode="env", api_key=""))
    ep = await reg.resolve_qwen_endpoint()
    assert ep.api_key is None


@pytest.mark.asyncio
async def test_env_mode_api_key_set() -> None:
    reg = EndpointRegistry(_settings(mode="env", api_key="secret-token"))
    ep = await reg.resolve_qwen_endpoint()
    assert ep.api_key == "secret-token"


# ---------------------------------------------------------------------------
# File mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_file_mode_reads_json(tmp_path: Path) -> None:
    f = tmp_path / "qwen_endpoint.json"
    f.write_text(
        json.dumps({
            "provider": "qwen",
            "model": "qwen3.6",
            "base_url": "https://abc-123.runpod.net",
            "timeout_seconds": 90,
            "updated_at": "2026-05-14T12:00:00Z",
        }),
        encoding="utf-8",
    )
    reg = EndpointRegistry(_settings(mode="file", registry_file=str(f)))
    ep = await reg.resolve_qwen_endpoint()
    assert ep.base_url == "https://abc-123.runpod.net"
    assert ep.model == "qwen3.6"
    assert ep.source == "file"
    assert ep.timeout_seconds == 90.0


@pytest.mark.asyncio
async def test_file_mode_strips_trailing_slash(tmp_path: Path) -> None:
    f = tmp_path / "qwen_endpoint.json"
    f.write_text(
        json.dumps({"base_url": "https://abc-123.runpod.net/"}),
        encoding="utf-8",
    )
    reg = EndpointRegistry(_settings(mode="file", registry_file=str(f)))
    ep = await reg.resolve_qwen_endpoint()
    assert ep.base_url == "https://abc-123.runpod.net"


@pytest.mark.asyncio
async def test_file_mode_raises_on_missing_base_url(tmp_path: Path) -> None:
    f = tmp_path / "qwen_endpoint.json"
    f.write_text(json.dumps({"model": "qwen3.6"}), encoding="utf-8")
    reg = EndpointRegistry(_settings(mode="file", registry_file=str(f)))
    with pytest.raises(ValueError, match="base_url"):
        await reg.resolve_qwen_endpoint()


@pytest.mark.asyncio
async def test_file_mode_raises_on_invalid_url(tmp_path: Path) -> None:
    f = tmp_path / "qwen_endpoint.json"
    f.write_text(json.dumps({"base_url": "ftp://bad-scheme.net"}), encoding="utf-8")
    reg = EndpointRegistry(_settings(mode="file", registry_file=str(f)))
    with pytest.raises(ValueError, match="Invalid endpoint URL"):
        await reg.resolve_qwen_endpoint()


@pytest.mark.asyncio
async def test_file_mode_fallback_to_env_when_file_missing() -> None:
    reg = EndpointRegistry(
        _settings(
            mode="file",
            base_url="http://env-fallback:9000",
            registry_file="/nonexistent/path/qwen_endpoint.json",
        )
    )
    ep = await reg.resolve_qwen_endpoint()
    assert ep.base_url == "http://env-fallback:9000"
    assert ep.source == "env_fallback"


# ---------------------------------------------------------------------------
# DB mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_db_mode_returns_active_row() -> None:
    from datetime import UTC, datetime

    mock_row = MagicMock()
    mock_row.provider = "qwen"
    mock_row.model = "qwen3.6"
    mock_row.base_url = "https://runpod-active.net"
    mock_row.updated_at = datetime(2026, 5, 14, 12, 0, tzinfo=UTC)

    mock_repo = AsyncMock()
    mock_repo.get_active.return_value = mock_row

    mock_session = AsyncMock()
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_factory = MagicMock(return_value=mock_session_ctx)

    reg = EndpointRegistry(_settings(mode="db"), session_factory=mock_factory)

    with patch(
        "app.repositories.runtime_endpoint_repository.RuntimeEndpointRepository",
        return_value=mock_repo,
    ):
        ep = await reg.resolve_qwen_endpoint()

    assert ep.base_url == "https://runpod-active.net"
    assert ep.source == "db"


@pytest.mark.asyncio
async def test_db_mode_fallback_to_env_when_no_row() -> None:
    mock_repo = AsyncMock()
    mock_repo.get_active.return_value = None

    mock_session = AsyncMock()
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_factory = MagicMock(return_value=mock_session_ctx)

    reg = EndpointRegistry(
        _settings(mode="db", base_url="http://env-db-fallback:8080"),
        session_factory=mock_factory,
    )

    with patch(
        "app.repositories.runtime_endpoint_repository.RuntimeEndpointRepository",
        return_value=mock_repo,
    ):
        ep = await reg.resolve_qwen_endpoint()

    assert ep.base_url == "http://env-db-fallback:8080"
    assert ep.source == "env_fallback"


# ---------------------------------------------------------------------------
# No network call during resolution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_network_call_during_resolution() -> None:
    """EndpointRegistry must not make HTTP calls when resolving the endpoint."""
    reg = EndpointRegistry(_settings(mode="env", base_url="http://localhost:8080"))

    with patch("httpx.AsyncClient") as mock_http:
        await reg.resolve_qwen_endpoint()

    mock_http.assert_not_called()
