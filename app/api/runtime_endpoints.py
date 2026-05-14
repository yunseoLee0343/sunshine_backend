"""Internal runtime endpoint registry API — TICKET-055.

Allows operators to update the active Qwen vLLM endpoint without image rebuild.
All routes require X-Internal-Token header (set INTERNAL_TOKEN in env).
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.repositories.runtime_endpoint_repository import RuntimeEndpointRepository
from app.schemas.runtime_endpoint import (
    RuntimeEndpointCheckResponse,
    RuntimeEndpointResponse,
    RuntimeEndpointUpdateRequest,
)

router = APIRouter(prefix="/internal/runtime-endpoints", tags=["internal"])

_ENDPOINT_NAME = "qwen_llm"


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session


def _require_token(x_internal_token: str | None = Header(None, alias="X-Internal-Token")) -> None:
    if not settings.INTERNAL_TOKEN:
        return  # token auth disabled (dev mode)
    if x_internal_token != settings.INTERNAL_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Internal-Token")


async def _perform_health_check(
    base_url: str,
    http_client: httpx.AsyncClient | None = None,
) -> tuple[str, str | None]:
    """Ping /v1/models and return (status, detail). No DB side effects."""
    try:
        if http_client is not None:
            resp = await http_client.get(f"{base_url}/v1/models")
        else:
            async with httpx.AsyncClient(timeout=10.0) as c:
                resp = await c.get(f"{base_url}/v1/models")
        if resp.status_code == 200:
            return "ok", None
        return "error", f"HTTP {resp.status_code}"
    except Exception as exc:
        return "error", str(exc)


@router.get(
    "/qwen",
    response_model=RuntimeEndpointResponse,
    summary="Get current Qwen endpoint",
)
async def get_qwen_endpoint(
    _: None = Depends(_require_token),
    session: AsyncSession = Depends(get_session),
) -> RuntimeEndpointResponse:
    repo = RuntimeEndpointRepository(session)
    row = await repo.get_active(_ENDPOINT_NAME)
    if row is None:
        return RuntimeEndpointResponse(
            name=_ENDPOINT_NAME,
            provider="qwen",
            model=settings.QWEN_LLM_MODEL,
            base_url=settings.QWEN_LLM_BASE_URL,
            health_status=None,
            updated_at=datetime.now(UTC),
        )
    return RuntimeEndpointResponse(
        name=row.name,
        provider=row.provider,
        model=row.model,
        base_url=row.base_url,
        health_status=row.health_status,
        updated_at=row.updated_at,
    )


@router.put(
    "/qwen",
    response_model=RuntimeEndpointResponse,
    summary="Update Qwen endpoint",
)
async def update_qwen_endpoint(
    body: RuntimeEndpointUpdateRequest,
    _: None = Depends(_require_token),
    session: AsyncSession = Depends(get_session),
) -> RuntimeEndpointResponse:
    from app.llm.endpoint_registry import _validate_url

    try:
        validated_url = _validate_url(body.base_url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    repo = RuntimeEndpointRepository(session)
    row = await repo.upsert_endpoint(
        name=_ENDPOINT_NAME,
        provider=body.provider,
        model=body.model,
        base_url=validated_url,
    )
    await session.commit()
    return RuntimeEndpointResponse(
        name=row.name,
        provider=row.provider,
        model=row.model,
        base_url=row.base_url,
        health_status=row.health_status,
        updated_at=row.updated_at,
    )


@router.post(
    "/qwen/check",
    response_model=RuntimeEndpointCheckResponse,
    summary="Health-check Qwen endpoint",
)
async def check_qwen_endpoint(
    _: None = Depends(_require_token),
    session: AsyncSession = Depends(get_session),
) -> RuntimeEndpointCheckResponse:
    """Ping /v1/models on the current Qwen endpoint and update health_status."""
    repo = RuntimeEndpointRepository(session)
    row = await repo.get_active(_ENDPOINT_NAME)
    base_url = row.base_url if row else settings.QWEN_LLM_BASE_URL

    checked_at = datetime.now(UTC)
    status, detail = await _perform_health_check(base_url)

    if row is not None:
        await repo.update_health(_ENDPOINT_NAME, status, checked_at)
        await session.commit()

    return RuntimeEndpointCheckResponse(
        endpoint=base_url,
        status=status,
        detail=detail,
        checked_at=checked_at,
    )
