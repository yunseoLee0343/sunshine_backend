"""ChunkBuildService — TICKET-047 (updated from TICKET-014B).

Reads 14A relational data, builds deterministic text chunks, embeds them
with a local model, and upserts results into plant_chunk_documents /
plant_chunk_embeddings. Idempotent: skips chunks whose text_hash is unchanged
AND whose embedding model/dim matches the current service.
"""

from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.chunk import ChunkBuildSummary
from app.embedding.chunk_builder import build_all_chunks
from app.models.plant_care_requirement import PlantCareRequirement
from app.models.plant_chunk_document import PlantChunkDocument
from app.models.plant_chunk_embedding import PlantChunkEmbedding
from app.models.plant_knowledge_entry import PlantKnowledgeEntry
from app.models.plant_pest_reference import PlantPestReference
from app.models.plant_placement import PlantPlacement
from app.models.plant_seasonal_watering import PlantSeasonalWatering
from app.models.plant_visual_trait import PlantVisualTrait

if TYPE_CHECKING:
    from app.embedding.local_embedding_service import LocalEmbeddingService


class ChunkBuildService:
    def __init__(
        self,
        session: AsyncSession,
        embedding_service: LocalEmbeddingService,
    ) -> None:
        self.session = session
        self.emb = embedding_service

    # ---------------------------------------------------------------------- public

    async def build_all(self) -> ChunkBuildSummary:
        result = await self.session.execute(select(PlantKnowledgeEntry))
        entries = result.scalars().all()
        summary = ChunkBuildSummary(total_entries=len(entries))
        for entry in entries:
            await self._build_entry(entry, summary)
        return summary

    async def build_for_entry(self, entry_id: uuid.UUID) -> ChunkBuildSummary:
        entry = await self.session.get(PlantKnowledgeEntry, entry_id)
        summary = ChunkBuildSummary(total_entries=1 if entry else 0)
        if entry is None:
            summary.errors += 1
            summary.error_details.append(f"entry {entry_id} not found")
            return summary
        await self._build_entry(entry, summary)
        return summary

    # ---------------------------------------------------------------------- private

    async def _build_entry(self, entry: PlantKnowledgeEntry, summary: ChunkBuildSummary) -> None:
        try:
            care = await self._get_one(PlantCareRequirement, entry.id)
            watering = await self._get_one(PlantSeasonalWatering, entry.id)
            pest = await self._get_one(PlantPestReference, entry.id)
            visual = await self._get_one(PlantVisualTrait, entry.id)
            placement = await self._get_one(PlantPlacement, entry.id)

            chunks = build_all_chunks(entry, care, watering, pest, visual, placement)

            texts_to_embed: list[str] = []
            chunks_needing_embed: list[int] = []
            docs: list[PlantChunkDocument | None] = []

            now = datetime.now(UTC)

            for i, chunk in enumerate(chunks):
                existing = await self._get_doc(entry.id, chunk.chunk_kind)
                if existing is not None and existing.text_hash == chunk.text_hash:
                    if await self._is_embedding_current(existing):
                        docs.append(existing)
                        summary.skipped += 1
                    else:
                        # Stale embedding (wrong model/dim) — re-embed without text change
                        docs.append(existing)
                        summary.updated += 1
                        texts_to_embed.append(chunk.text)
                        chunks_needing_embed.append(i)
                else:
                    if existing is not None:
                        existing.chunk_text = chunk.text
                        existing.text_hash = chunk.text_hash
                        existing.updated_at = now
                        docs.append(existing)
                        summary.updated += 1
                    else:
                        doc = PlantChunkDocument(
                            id=uuid.uuid4(),
                            plant_knowledge_id=entry.id,
                            chunk_kind=chunk.chunk_kind,
                            chunk_text=chunk.text,
                            text_hash=chunk.text_hash,
                            created_at=now,
                            updated_at=now,
                        )
                        self.session.add(doc)
                        docs.append(doc)
                        summary.inserted += 1
                    texts_to_embed.append(chunk.text)
                    chunks_needing_embed.append(i)

            if texts_to_embed:
                await self.session.flush()
                vectors = self.emb.embed_batch(texts_to_embed)
                for idx, vec in zip(chunks_needing_embed, vectors):
                    doc = docs[idx]
                    chunk = chunks[idx]
                    await self._upsert_embedding(doc, vec, now, chunk.text_hash)  # type: ignore[arg-type]

        except Exception as exc:  # noqa: BLE001
            summary.errors += 1
            summary.error_details.append(f"entry {entry.id}: {exc}")

    async def _is_embedding_current(self, doc: PlantChunkDocument) -> bool:
        """Return True when the stored embedding matches the current model name and dim."""
        result = await self.session.execute(
            select(PlantChunkEmbedding).where(PlantChunkEmbedding.chunk_document_id == doc.id)
        )
        emb = result.scalar_one_or_none()
        if emb is None:
            return False
        return emb.model_name == self.emb.model_name and emb.vector_dim == self.emb.embedding_dim

    async def _get_one(self, model, entry_id: uuid.UUID):
        result = await self.session.execute(select(model).where(model.entry_id == entry_id))
        return result.scalar_one_or_none()

    async def _get_doc(self, plant_knowledge_id: uuid.UUID, chunk_kind: str) -> PlantChunkDocument | None:
        result = await self.session.execute(
            select(PlantChunkDocument).where(
                PlantChunkDocument.plant_knowledge_id == plant_knowledge_id,
                PlantChunkDocument.chunk_kind == chunk_kind,
            )
        )
        return result.scalar_one_or_none()

    async def _upsert_embedding(
        self,
        doc: PlantChunkDocument,
        vector: list[float],
        now: datetime,
        text_hash: str | None = None,
    ) -> None:
        norm = math.sqrt(sum(x * x for x in vector))
        result = await self.session.execute(
            select(PlantChunkEmbedding).where(PlantChunkEmbedding.chunk_document_id == doc.id)
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            existing.vector = vector
            existing.vector_dim = len(vector)
            existing.model_name = self.emb.model_name
            existing.vector_norm = norm
            existing.text_hash_at_embed = text_hash
            existing.updated_at = now
        else:
            self.session.add(
                PlantChunkEmbedding(
                    id=uuid.uuid4(),
                    chunk_document_id=doc.id,
                    model_name=self.emb.model_name,
                    vector_dim=len(vector),
                    vector=vector,
                    vector_norm=norm,
                    text_hash_at_embed=text_hash,
                    created_at=now,
                    updated_at=now,
                )
            )
        await self.session.flush()
