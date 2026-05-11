"""Retrieval API schemas — TICKET-014C."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.domain.retrieval import ALL_RAG_LAYERS, RagLayer


class RetrievalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: uuid.UUID
    user_id: uuid.UUID
    question: str = Field(..., min_length=1, max_length=2000)
    species_profile_id: uuid.UUID | None = None
    rag_layers: list[RagLayer] = Field(default_factory=lambda: list(ALL_RAG_LAYERS))
    top_k: int = Field(default=5, ge=1, le=20)


class ChunkResultItem(BaseModel):
    rank: int
    chunk_document_id: uuid.UUID
    plant_knowledge_id: uuid.UUID
    chunk_kind: str
    chunk_text: str
    similarity_score: float


class RetrievalResponse(BaseModel):
    request_id: uuid.UUID
    question: str
    total_results: int
    from_cache: bool
    results: list[ChunkResultItem]
