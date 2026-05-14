"""TICKET-055 — runtime endpoint API tests."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c


def _make_row(
    base_url: str = "https://runpod-active.net",
    model: str = "qwen3.6",
    provider: str = "qwen",
    health_status: str = "unknown",
):
    row = MagicMock()
    row.name = "qwen_llm"
    row.provider = provider
    row.model = model
    row.base_url = base_url
    row.health_status = health_status
    row.updated_at = datetime(2026, 5, 14, 12, 0, tzinfo=UTC)
    return row


# ---------------------------------------------------------------------------
# GET /internal/runtime-endpoints/qwen
# ---------------------------------------------------------------------------


def test_get_qwen_endpoint_no_db_row(client) -> None:
    """When no row exists, env config values are returned."""
    mock_repo = AsyncMock()
    mock_repo.get_active.return_value = None

    with (
        patch("app.api.runtime_endpoints.RuntimeEndpointRepository", return_value=mock_repo),
        patch("app.api.runtime_endpoints.settings") as mock_settings,
    ):
        mock_settings.INTERNAL_TOKEN = ""
        mock_settings.QWEN_LLM_MODEL = "qwen3.6"
        mock_settings.QWEN_LLM_BASE_URL = "http://localhost:8080"

        resp = client.get("/internal/runtime-endpoints/qwen")

    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "qwen_llm"
    assert data["base_url"] == "http://localhost:8080"


def test_get_qwen_endpoint_returns_db_row(client) -> None:
    row = _make_row(base_url="https://runpod-active.net")
    mock_repo = AsyncMock()
    mock_repo.get_active.return_value = row

    with (
        patch("app.api.runtime_endpoints.RuntimeEndpointRepository", return_value=mock_repo),
        patch("app.api.runtime_endpoints.settings") as mock_settings,
    ):
        mock_settings.INTERNAL_TOKEN = ""
        resp = client.get("/internal/runtime-endpoints/qwen")

    assert resp.status_code == 200
    data = resp.json()
    assert data["base_url"] == "https://runpod-active.net"
    assert "api_key" not in data  # raw secret must not be exposed


# ---------------------------------------------------------------------------
# PUT /internal/runtime-endpoints/qwen
# ---------------------------------------------------------------------------


def test_put_qwen_endpoint_updates_base_url(client) -> None:
    row = _make_row(base_url="https://new-runpod.net")
    mock_repo = AsyncMock()
    mock_repo.upsert_endpoint.return_value = row

    with (
        patch("app.api.runtime_endpoints.RuntimeEndpointRepository", return_value=mock_repo),
        patch("app.api.runtime_endpoints.settings") as mock_settings,
    ):
        mock_settings.INTERNAL_TOKEN = ""
        resp = client.put(
            "/internal/runtime-endpoints/qwen",
            json={"base_url": "https://new-runpod.net", "model": "qwen3.6", "provider": "qwen"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["base_url"] == "https://new-runpod.net"


def test_put_qwen_endpoint_missing_token_rejected(client) -> None:
    with patch("app.api.runtime_endpoints.settings") as mock_settings:
        mock_settings.INTERNAL_TOKEN = "secret-token"
        resp = client.put(
            "/internal/runtime-endpoints/qwen",
            json={"base_url": "https://new-runpod.net", "model": "qwen3.6", "provider": "qwen"},
        )
    assert resp.status_code == 401


def test_put_qwen_endpoint_invalid_url_rejected(client) -> None:
    with patch("app.api.runtime_endpoints.settings") as mock_settings:
        mock_settings.INTERNAL_TOKEN = ""
        resp = client.put(
            "/internal/runtime-endpoints/qwen",
            json={"base_url": "ftp://invalid-scheme.net", "model": "qwen3.6", "provider": "qwen"},
        )
    assert resp.status_code == 422


def test_put_qwen_endpoint_valid_token_accepted(client) -> None:
    row = _make_row(base_url="https://new-runpod.net")
    mock_repo = AsyncMock()
    mock_repo.upsert_endpoint.return_value = row

    with (
        patch("app.api.runtime_endpoints.RuntimeEndpointRepository", return_value=mock_repo),
        patch("app.api.runtime_endpoints.settings") as mock_settings,
    ):
        mock_settings.INTERNAL_TOKEN = "my-token"
        resp = client.put(
            "/internal/runtime-endpoints/qwen",
            headers={"X-Internal-Token": "my-token"},
            json={"base_url": "https://new-runpod.net", "model": "qwen3.6", "provider": "qwen"},
        )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# _perform_health_check (unit tests with mocked HTTP transport)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_perform_health_check_ok() -> None:
    from app.api.runtime_endpoints import _perform_health_check

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200

    mock_http = AsyncMock(spec=httpx.AsyncClient)
    mock_http.get = AsyncMock(return_value=mock_resp)

    status, detail = await _perform_health_check("https://runpod.net", http_client=mock_http)

    assert status == "ok"
    assert detail is None
    mock_http.get.assert_awaited_once_with("https://runpod.net/v1/models")


@pytest.mark.asyncio
async def test_perform_health_check_non_200_returns_error() -> None:
    from app.api.runtime_endpoints import _perform_health_check

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 503

    mock_http = AsyncMock(spec=httpx.AsyncClient)
    mock_http.get = AsyncMock(return_value=mock_resp)

    status, detail = await _perform_health_check("https://runpod.net", http_client=mock_http)

    assert status == "error"
    assert "503" in (detail or "")


@pytest.mark.asyncio
async def test_perform_health_check_network_error_returns_error() -> None:
    from app.api.runtime_endpoints import _perform_health_check

    mock_http = AsyncMock(spec=httpx.AsyncClient)
    mock_http.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))

    status, detail = await _perform_health_check("https://runpod.net", http_client=mock_http)

    assert status == "error"
    assert detail is not None
