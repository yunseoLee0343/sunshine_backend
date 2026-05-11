"""ForwardContext domain types — TICKET-015.

ForwardContext is a frozen, serialisable bundle assembled from data across
prior tickets (rule engine, character, snapshot, care logs, retrieved chunks).
It is hashed deterministically and stored as a single JSONB blob so downstream
consumers (future prompt builder) always get a stable, auditable snapshot.

No LLM, no prompt construction, no answer generation.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Component evidence types (all use plain JSON-serialisable Python types)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CharacterEvidence:
    mood: str
    expression: str
    status_message: str
    primary_action: str
    reason_code: str


@dataclass(frozen=True)
class SnapshotEvidence:
    window: str
    temperature_avg_c: float | None
    humidity_avg_pct: float | None
    light_avg_lux: float | None
    soil_moisture_avg_pct: float | None


@dataclass(frozen=True)
class CareLogEvidence:
    action_type: str
    note: str | None
    acted_at: str  # ISO-8601 UTC string


@dataclass(frozen=True)
class ChunkEvidence:
    chunk_document_id: str  # UUID as str for JSON-safety
    plant_knowledge_id: str
    chunk_kind: str
    chunk_text: str
    similarity_score: float
    rank: int


# ---------------------------------------------------------------------------
# ForwardContext
# ---------------------------------------------------------------------------


@dataclass
class ForwardContext:
    plant_id: str  # UUID as str
    user_id: str
    question: str
    intent: str
    rag_layers: list[str]
    character: CharacterEvidence | None
    snapshot: SnapshotEvidence | None
    recent_care_logs: list[CareLogEvidence]
    rule_evidence_facts: dict[str, Any]
    rule_reason_codes: list[str]
    rule_primary_action: str
    retrieved_chunks: list[ChunkEvidence]
    source_coverage: dict[str, bool]  # layer → at least one chunk retrieved
    visual_facts: list[str] = field(default_factory=list)
    # Computed last — not included in the hash input itself
    evidence_hash: str = field(default="", compare=False)

    # ------------------------------------------------------------------

    @classmethod
    def build(
        cls,
        *,
        plant_id: uuid.UUID,
        user_id: uuid.UUID,
        question: str,
        intent: str,
        rag_layers: list[str],
        character: CharacterEvidence | None,
        snapshot: SnapshotEvidence | None,
        recent_care_logs: list[CareLogEvidence],
        rule_evidence_facts: dict[str, Any],
        rule_reason_codes: list[str],
        rule_primary_action: str,
        retrieved_chunks: list[ChunkEvidence],
        source_coverage: dict[str, bool],
        visual_facts: list[str] | None = None,
    ) -> ForwardContext:
        ctx = cls(
            plant_id=str(plant_id),
            user_id=str(user_id),
            question=question,
            intent=intent,
            rag_layers=sorted(rag_layers),
            character=character,
            snapshot=snapshot,
            recent_care_logs=recent_care_logs,
            rule_evidence_facts=rule_evidence_facts,
            rule_reason_codes=rule_reason_codes,
            rule_primary_action=rule_primary_action,
            retrieved_chunks=retrieved_chunks,
            source_coverage=source_coverage,
            visual_facts=list(visual_facts) if visual_facts else [],
        )
        ctx.evidence_hash = _compute_hash(ctx)
        return ctx

    def to_dict(self) -> dict[str, Any]:
        return _to_serialisable(asdict(self))


# ---------------------------------------------------------------------------
# Hash helpers
# ---------------------------------------------------------------------------


def _to_serialisable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _to_serialisable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_serialisable(v) for v in obj]
    return obj


def _compute_hash(ctx: ForwardContext) -> str:
    """SHA-256 of the normalised JSON of ctx, excluding the hash field itself."""
    d = asdict(ctx)
    d.pop("evidence_hash", None)
    canonical = json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
