"""Audit view schemas — TICKET-022.

ChatRunEvidenceView is the single response type for
GET /chat-runs/{request_id}/evidence.  It is assembled from three existing
tables (ChatRequest, LlmRun, EvidenceBundle) — no new tables required.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class SnapshotSummary(BaseModel):
    window: str
    temperature_avg_c: float | None
    humidity_avg_pct: float | None
    light_avg_lux: float | None
    soil_moisture_avg_pct: float | None


class ChunkSummary(BaseModel):
    chunk_document_id: str
    chunk_kind: str
    chunk_text: str
    similarity_score: float
    rank: int


class ChatRunEvidenceView(BaseModel):
    request_id: uuid.UUID
    plant_id: uuid.UUID | None
    question: str
    intent: str
    rag_layers: list[str]
    # LLM run data
    prompt_hash: str
    prompt_text: str
    response_text: str
    model_name: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    # Integrity: SHA-256(prompt_text) == prompt_hash
    is_prompt_hash_valid: bool
    # Evidence data (None / empty for companion branch or missing snapshot)
    evidence_hash: str | None
    sensor_snapshot: SnapshotSummary | None
    rule_primary_action: str | None
    rule_reason_codes: list[str]
    rule_evidence_facts: dict
    retrieved_chunks: list[ChunkSummary]
    source_coverage: dict[str, bool]
    created_at: datetime
