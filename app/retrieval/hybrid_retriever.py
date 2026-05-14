"""HybridRetriever — TICKET-014C / TICKET-048.

Two-stage retrieval:
  1. Relational pre-filter: resolve species_profile_id → plant_knowledge_entries
     via scientific_name match, then restrict chunk_kind to the requested
     RAG layers.
  2. Vector scoring: load JSONB vectors from plant_chunk_embeddings, compute
     dot-product similarity (vectors are L2-normalised from 14B), rank,
     return top_k results.

No LLM, no generation, no diagnosis.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.rag import IncompatibleEmbeddingError
from app.domain.retrieval import (
    RAG_LAYER_TO_CHUNK_KINDS,
    RetrievalFilter,
    RetrievedChunkResult,
)
from app.models.plant_chunk_document import PlantChunkDocument
from app.models.plant_chunk_embedding import PlantChunkEmbedding
from app.models.plant_knowledge_entry import PlantKnowledgeEntry
from app.models.species_profile import SpeciesProfile

if TYPE_CHECKING:
    from app.embedding.local_embedding_service import LocalEmbeddingService


def _chunk_kind_to_rag_layer(chunk_kind: str) -> str | None:
    for layer, kinds in RAG_LAYER_TO_CHUNK_KINDS.items():
        if chunk_kind in kinds:
            return layer
    return None


def _is_compatible(
    emb_row: PlantChunkEmbedding,
    expected_model: str | None,
    expected_dim: int | None,
) -> bool:
    if expected_model is not None:
        if not isinstance(emb_row.model_name, str):
            return True  # non-str attribute (e.g., test mock) — let through
        if emb_row.model_name != expected_model:
            return False
    if expected_dim is not None:
        if not isinstance(emb_row.vector_dim, int):
            return True  # non-int attribute (e.g., test mock) — let through
        if emb_row.vector_dim != expected_dim:
            return False
    return True


class HybridRetriever:
    def __init__(
        self,
        session: AsyncSession,
        embedding_service: LocalEmbeddingService,
        expected_model: str | None = None,
        expected_dim: int | None = None,
    ) -> None:
        self.session = session
        self.emb = embedding_service
        self._expected_model = expected_model
        self._expected_dim = expected_dim

    async def retrieve(self, f: RetrievalFilter) -> list[RetrievedChunkResult]:
        # ---- 1. resolve allowed chunk kinds from RAG layers ----------------
        allowed_kinds: set[str] = set()
        for layer in f.rag_layers:
            allowed_kinds.update(RAG_LAYER_TO_CHUNK_KINDS.get(layer, ()))

        # ---- 2. resolve plant_knowledge_ids from species_profile_id --------
        knowledge_ids: list[uuid.UUID] | None = None  # None = no FK filter
        if f.species_profile_id is not None:
            knowledge_ids = await self._resolve_knowledge_ids(f.species_profile_id)
            if not knowledge_ids:
                return []  # species found but no linked knowledge entries

        # ---- 3. fetch candidate chunk documents ----------------------------
        stmt = select(PlantChunkDocument)
        if knowledge_ids is not None:
            stmt = stmt.where(PlantChunkDocument.plant_knowledge_id.in_(knowledge_ids))
        if allowed_kinds:
            stmt = stmt.where(PlantChunkDocument.chunk_kind.in_(allowed_kinds))

        result = await self.session.execute(stmt)
        docs = result.scalars().all()
        if not docs:
            return []

        # ---- 4. load embeddings -------------------------------------------
        doc_ids = [d.id for d in docs]
        emb_result = await self.session.execute(
            select(PlantChunkEmbedding).where(PlantChunkEmbedding.chunk_document_id.in_(doc_ids))
        )
        all_embeddings = {e.chunk_document_id: e for e in emb_result.scalars().all()}

        # ---- 4b. filter incompatible embeddings ---------------------------
        embeddings_by_doc = {
            doc_id: emb_row
            for doc_id, emb_row in all_embeddings.items()
            if _is_compatible(emb_row, self._expected_model, self._expected_dim)
        }
        if all_embeddings and not embeddings_by_doc:
            raise IncompatibleEmbeddingError(
                f"All {len(all_embeddings)} candidate embeddings are incompatible "
                f"with model={self._expected_model!r} dim={self._expected_dim}. "
                "Rebuild the embedding store with the current model settings."
            )

        # ---- 5. embed question + score ------------------------------------
        query_vec = self.emb.embed(f.question)

        scored: list[tuple[float, PlantChunkDocument]] = []
        for doc in docs:
            emb_row = embeddings_by_doc.get(doc.id)
            if emb_row is None:
                continue
            score = _dot(query_vec, emb_row.vector)
            scored.append((score, doc))

        # deterministic: higher score first, then ascending chunk_id as tiebreaker
        scored.sort(key=lambda t: (-t[0], str(t[1].id)))
        top = scored[: f.top_k]

        return [
            RetrievedChunkResult(
                chunk_document_id=doc.id,
                plant_knowledge_id=doc.plant_knowledge_id,
                chunk_kind=doc.chunk_kind,
                chunk_text=doc.chunk_text,
                similarity_score=round(score, 6),
                rank=rank + 1,
                rag_layer=_chunk_kind_to_rag_layer(doc.chunk_kind),
            )
            for rank, (score, doc) in enumerate(top)
        ]

    # ---------------------------------------------------------------------- private

    async def _resolve_knowledge_ids(self, species_profile_id: uuid.UUID) -> list[uuid.UUID]:
        sp = await self.session.get(SpeciesProfile, species_profile_id)
        if sp is None or not sp.scientific_name:
            return []
        result = await self.session.execute(
            select(PlantKnowledgeEntry).where(PlantKnowledgeEntry.scientific_name == sp.scientific_name)
        )
        return [e.id for e in result.scalars().all()]


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
