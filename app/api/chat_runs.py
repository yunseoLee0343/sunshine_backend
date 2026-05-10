"""Chat run evidence audit API — TICKET-022.

GET /chat-runs/{request_id}/evidence
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.schemas.audit_view import ChatRunEvidenceView
from app.services.audit_query_service import AuditQueryService, ChatRunNotFoundError

router = APIRouter(prefix="/chat-runs", tags=["audit"])


async def _get_session():
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/{request_id}/evidence", response_model=ChatRunEvidenceView)
async def get_chat_run_evidence(
    request_id: uuid.UUID,
    session: AsyncSession = Depends(_get_session),
) -> ChatRunEvidenceView:
    """Return the full decision evidence for a completed chat run.

    Assembles question, intent, selected RAG layers, sensor snapshot,
    rule engine results, retrieved knowledge chunks, prompt text, and
    model response from persisted records.  Includes a prompt_hash
    integrity flag.
    """
    svc = AuditQueryService(session)
    try:
        return await svc.get_evidence(request_id)
    except ChatRunNotFoundError:
        raise HTTPException(status_code=404, detail="chat run not found")
