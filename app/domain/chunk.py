"""Chunk domain types — TICKET-014B."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Literal

ChunkKind = Literal[
    "identity",
    "care_requirement",
    "seasonal_watering",
    "pest_reference",
    "visual_trait",
    "placement",
]

CHUNK_KINDS: tuple[ChunkKind, ...] = (
    "identity",
    "care_requirement",
    "seasonal_watering",
    "pest_reference",
    "visual_trait",
    "placement",
)


@dataclass(frozen=True)
class BuiltChunk:
    plant_knowledge_id: uuid.UUID
    chunk_kind: ChunkKind
    text: str
    text_hash: str  # SHA-256 hex of text (utf-8)


@dataclass
class ChunkBuildSummary:
    total_entries: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0
    error_details: list[str] = field(default_factory=list)
