"""Evidence bundle API schemas — TICKET-015."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.retrieval import ALL_RAG_LAYERS, RagLayer
from app.schemas.chat_intent import Intent


class EvidenceBuildRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plant_id: uuid.UUID
    user_id: uuid.UUID
    question: str = Field(..., min_length=1, max_length=2000)
    intent: Intent
    rag_layers: list[RagLayer] = Field(default_factory=lambda: list(ALL_RAG_LAYERS))
    retrieval_run_id: uuid.UUID | None = None  # load chunks from existing retrieval run
    visual_facts: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Response sub-types
# ---------------------------------------------------------------------------


class CharacterEvidenceOut(BaseModel):
    mood: str
    expression: str
    status_message: str
    primary_action: str
    reason_code: str


class SnapshotEvidenceOut(BaseModel):
    window: str
    temperature_avg_c: float | None
    humidity_avg_pct: float | None
    light_avg_lux: float | None
    soil_moisture_avg_pct: float | None


class CareLogEvidenceOut(BaseModel):
    action_type: str
    note: str | None
    acted_at: str


class ChunkEvidenceOut(BaseModel):
    chunk_document_id: str
    plant_knowledge_id: str
    chunk_kind: str
    chunk_text: str
    similarity_score: float
    rank: int


class EvidenceBundleResponse(BaseModel):
    evidence_hash: str
    plant_id: uuid.UUID
    user_id: uuid.UUID
    question: str
    intent: str
    rag_layers: list[str]
    character: CharacterEvidenceOut | None
    snapshot: SnapshotEvidenceOut | None
    recent_care_logs: list[CareLogEvidenceOut]
    rule_evidence_facts: dict[str, Any]
    rule_reason_codes: list[str]
    rule_primary_action: str
    retrieved_chunks: list[ChunkEvidenceOut]
    source_coverage: dict[str, bool]
    from_cache: bool
