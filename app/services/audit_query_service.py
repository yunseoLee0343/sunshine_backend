"""AuditQueryService — TICKET-022.

Thin service layer over AuditRepository.  Converts a missing result into a
domain exception so the API layer can produce the correct HTTP status.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.audit_repository import AuditRepository
from app.schemas.audit_view import ChatRunEvidenceView


class ChatRunNotFoundError(Exception):
    """Raised when the requested chat run does not exist."""


class AuditQueryService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = AuditRepository(session)

    async def get_evidence(self, request_id: uuid.UUID) -> ChatRunEvidenceView:
        view = await self._repo.get_chat_run_evidence(request_id)
        if view is None:
            raise ChatRunNotFoundError(f"chat run {request_id} not found")
        return view
