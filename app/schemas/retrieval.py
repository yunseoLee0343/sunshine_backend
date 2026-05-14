"""Retrieval API schemas — TICKET-014C / TICKET-048."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.retrieval import ALL_RAG_LAYERS, RagLayer


class RetrievalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: uuid.UUID
    user_id: uuid.UUID
    plant_id: uuid.UUID | None = None
    question: str = Field(..., min_length=1, max_length=2000)
    species_profile_id: uuid.UUID | None = None
    rag_layers: list[RagLayer] = Field(default_factory=lambda: list(ALL_RAG_LAYERS))
    top_k: int = Field(default=5, ge=1, le=20)

    @model_validator(mode="before")
    @classmethod
    def _normalise_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            if "query" in data and "question" not in data:
                data["question"] = data.pop("query")
            if "selected_rag_layers" in data and "rag_layers" not in data:
                data["rag_layers"] = data.pop("selected_rag_layers")
        return data


class ChunkResultItem(BaseModel):
    rank: int
    chunk_document_id: uuid.UUID
    plant_knowledge_id: uuid.UUID
    chunk_kind: str
    chunk_text: str
    similarity_score: float
    layer: str | None = None
    source_metadata: dict | None = None
    structured_metadata: dict | None = None


class RetrievalResponse(BaseModel):
    request_id: uuid.UUID
    question: str
    total_results: int
    from_cache: bool
    results: list[ChunkResultItem]
