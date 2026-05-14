"""EmbeddingRepository — TICKET-047. Read-only. No retrieval API."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plant_chunk_embedding import PlantChunkEmbedding


class EmbeddingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_chunk_document_id(
        self, chunk_document_id: uuid.UUID
    ) -> PlantChunkEmbedding | None:
        result = await self.session.execute(
            select(PlantChunkEmbedding).where(
                PlantChunkEmbedding.chunk_document_id == chunk_document_id
            )
        )
        return result.scalar_one_or_none()

    async def list_stale(
        self,
        expected_model_name: str,
        expected_vector_dim: int,
    ) -> list[PlantChunkEmbedding]:
        """Return embeddings whose model_name or vector_dim differ from expected values."""
        result = await self.session.execute(
            select(PlantChunkEmbedding).where(
                (PlantChunkEmbedding.model_name != expected_model_name)
                | (PlantChunkEmbedding.vector_dim != expected_vector_dim)
            )
        )
        return list(result.scalars().all())

    async def count_dim_mismatch(self, expected_dim: int) -> int:
        """Return count of rows where vector_dim != expected_dim."""
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count()).where(PlantChunkEmbedding.vector_dim != expected_dim)
        )
        return result.scalar_one()
