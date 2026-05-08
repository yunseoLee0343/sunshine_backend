"""TICKET-001 — /healthz contract (Ticket 1 perspective).

Verifies that /healthz remains liveness-only even after DB layer is added.
"""

import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import app

EXPECTED_BODY = {"status": "ok", "service": "sunshine-backend"}


async def _get(path: str) -> tuple[int, dict]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get(path)
    return r.status_code, r.json()


def test_healthz_returns_200() -> None:
    status, _ = asyncio.run(_get("/healthz"))
    assert status == 200


def test_healthz_exact_json() -> None:
    _, body = asyncio.run(_get("/healthz"))
    assert body == EXPECTED_BODY


def test_healthz_response_has_no_db_fields() -> None:
    """Response must not expose DB status, checks, or any dynamic field."""
    _, body = asyncio.run(_get("/healthz"))
    assert "checks" not in body
    assert "database" not in body
    assert "timestamp" not in body
    assert "version" not in body
    assert set(body.keys()) == {"status", "service"}
