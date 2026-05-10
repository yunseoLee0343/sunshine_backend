"""ChunkRepository — TICKET-014B. Read-only. No search/retrieval API."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plant_chunk_document import PlantChunkDocument
from app.models.plant_chunk_embedding import PlantChunkEmbedding


class ChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_document(
        self, plant_knowledge_id: uuid.UUID, chunk_kind: str
    ) -> PlantChunkDocument | None:
        result = await self.session.execute(
            select(PlantChunkDocument).where(
                PlantChunkDocument.plant_knowledge_id == plant_knowledge_id,
                PlantChunkDocument.chunk_kind == chunk_kind,
            )
        )
        return result.scalar_one_or_none()

    async def list_documents(
        self, plant_knowledge_id: uuid.UUID
    ) -> list[PlantChunkDocument]:
        result = await self.session.execute(
            select(PlantChunkDocument).where(
                PlantChunkDocument.plant_knowledge_id == plant_knowledge_id
            )
        )
        return list(result.scalars().all())

    async def get_embedding(
        self, chunk_document_id: uuid.UUID
    ) -> PlantChunkEmbedding | None:
        return await self.session.get(PlantChunkEmbedding, chunk_document_id)
