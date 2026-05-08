"""TICKET-001 — /readyz contract tests.

Uses unittest.mock to simulate DB up/down states without a live Postgres.
"""

import asyncio
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from app.main import app

READY_BODY = {
    "status": "ready",
    "service": "sunshine-backend",
    "checks": {"database": "ok"},
}
NOT_READY_BODY = {
    "status": "not_ready",
    "service": "sunshine-backend",
    "checks": {"database": "error"},
}


async def _get(path: str) -> tuple[int, dict]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get(path)
    return r.status_code, r.json()


def test_readyz_db_ok_returns_200() -> None:
    """When DB is reachable, /readyz must return 200."""
    with patch("app.main.check_db", new=AsyncMock(return_value=True)):
        status, _ = asyncio.run(_get("/readyz"))
    assert status == 200


def test_readyz_db_ok_exact_json() -> None:
    """When DB is reachable, response must match exact contract."""
    with patch("app.main.check_db", new=AsyncMock(return_value=True)):
        _, body = asyncio.run(_get("/readyz"))
    assert body == READY_BODY


def test_readyz_db_down_returns_503() -> None:
    """When DB is unreachable, /readyz must return 503."""
    with patch("app.main.check_db", new=AsyncMock(return_value=False)):
        status, _ = asyncio.run(_get("/readyz"))
    assert status == 503


def test_readyz_db_down_exact_json() -> None:
    """When DB is unreachable, response must match exact not_ready contract."""
    with patch("app.main.check_db", new=AsyncMock(return_value=False)):
        _, body = asyncio.run(_get("/readyz"))
    assert body == NOT_READY_BODY


def test_readyz_checks_only_database() -> None:
    """checks dict must contain only 'database' — no redis/mqtt/llm keys."""
    with patch("app.main.check_db", new=AsyncMock(return_value=True)):
        _, body = asyncio.run(_get("/readyz"))
    assert set(body["checks"].keys()) == {"database"}
