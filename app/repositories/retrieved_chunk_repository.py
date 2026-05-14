"""RetrievedChunkRepository — TICKET-048."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.retrieval_result_chunk import RetrievalResultChunk
from app.repositories.base_repository import BaseRepository


class RetrievedChunkRepository(BaseRepository[RetrievalResultChunk]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(RetrievalResultChunk, session)

    async def list_by_run(self, run_id: uuid.UUID) -> list[RetrievalResultChunk]:
        result = await self.session.execute(
            select(RetrievalResultChunk)
            .where(RetrievalResultChunk.run_id == run_id)
            .order_by(RetrievalResultChunk.rank)
        )
        return list(result.scalars().all())

    async def count_by_run(self, run_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(RetrievalResultChunk).where(RetrievalResultChunk.run_id == run_id)
        )
        return len(result.scalars().all())
