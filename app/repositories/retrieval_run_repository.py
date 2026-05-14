"""RetrievalRunRepository — TICKET-048."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.retrieval_run import RetrievalRun
from app.repositories.base_repository import BaseRepository


class RetrievalRunRepository(BaseRepository[RetrievalRun]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(RetrievalRun, session)

    async def get_by_request_id(self, request_id: uuid.UUID) -> RetrievalRun | None:
        return await self.get(request_id)

    async def list_by_user(self, user_id: uuid.UUID, limit: int = 20) -> list[RetrievalRun]:
        result = await self.session.execute(
            select(RetrievalRun)
            .where(RetrievalRun.user_id == user_id)
            .order_by(RetrievalRun.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_embedding_model(self, model_name: str) -> list[RetrievalRun]:
        result = await self.session.execute(
            select(RetrievalRun).where(RetrievalRun.model_name == model_name)
        )
        return list(result.scalars().all())
