"""Retrieval domain types — TICKET-014C."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Literal

from app.domain.chunk import ChunkKind

RagLayer = Literal["species_profile", "care_knowledge", "pest_disease_reference"]

ALL_RAG_LAYERS: tuple[RagLayer, ...] = (
    "species_profile",
    "care_knowledge",
    "pest_disease_reference",
)

# Which ChunkKinds are searched per RAG layer
RAG_LAYER_TO_CHUNK_KINDS: dict[str, tuple[ChunkKind, ...]] = {
    "species_profile": ("identity", "visual_trait", "placement"),
    "care_knowledge": ("care_requirement", "seasonal_watering"),
    "pest_disease_reference": ("pest_reference",),
}


@dataclass(frozen=True)
class RetrievalFilter:
    question: str
    species_profile_id: uuid.UUID | None  # None → no relational pre-filter
    rag_layers: tuple[str, ...]
    top_k: int


@dataclass(frozen=True)
class RetrievedChunkResult:
    chunk_document_id: uuid.UUID
    plant_knowledge_id: uuid.UUID
    chunk_kind: str
    chunk_text: str
    similarity_score: float
    rank: int


@dataclass
class RetrievalRunResult:
    request_id: uuid.UUID
    question: str
    results: list[RetrievedChunkResult] = field(default_factory=list)
    from_cache: bool = False
