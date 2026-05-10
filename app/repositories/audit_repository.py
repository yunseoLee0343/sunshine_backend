"""AuditRepository — TICKET-022.

Read-only.  Assembles ChatRunEvidenceView from three tables that the
ChatOrchestrator already writes on every successful run:

  ChatRequest   → question, intent (status), plant_id, created_at
  LlmRun        → prompt_text, prompt_hash, response_text, model, tokens
  EvidenceBundle→ rag_layers, sensor snapshot, rule results, chunks, coverage

No new rows are written here; the existing persistence is sufficient.

Integrity check: SHA-256(prompt_text) is compared to the stored prompt_hash.
The companion branch uses a different hash scheme so its validity flag is
always False — this is expected and documented in the view payload.
"""

from __future__ import annotations

import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_request import ChatRequest
from app.models.evidence_bundle import EvidenceBundle
from app.models.llm_run import LlmRun
from app.schemas.audit_view import (
    ChatRunEvidenceView,
    ChunkSummary,
    SnapshotSummary,
)

_COMPANION_INTENT = "companion_plant_question"


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_chat_run_evidence(
        self, request_id: uuid.UUID
    ) -> ChatRunEvidenceView | None:
        # 1. ChatRequest — not found → 404
        chat = await self.session.get(ChatRequest, request_id)
        if chat is None:
            return None

        # 2. LlmRun — one per request_id in normal and companion paths
        result = await self.session.execute(
            select(LlmRun)
            .where(LlmRun.request_id == request_id)
            .limit(1)
        )
        llm_run = result.scalar_one_or_none()

        # 3. EvidenceBundle — skipped for companion (no evidence pipeline)
        bundle: EvidenceBundle | None = None
        if chat.plant_id is not None and chat.status != _COMPANION_INTENT:
            result = await self.session.execute(
                select(EvidenceBundle)
                .where(
                    EvidenceBundle.plant_id == chat.plant_id,
                    EvidenceBundle.question == chat.question,
                    EvidenceBundle.intent == chat.status,
                )
                .order_by(EvidenceBundle.created_at.desc())
                .limit(1)
            )
            bundle = result.scalar_one_or_none()

        return _assemble(chat, llm_run, bundle)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _check_hash(prompt_text: str | None, prompt_hash: str | None) -> bool:
    """Return True iff SHA-256(prompt_text) matches stored prompt_hash."""
    if not prompt_text or not prompt_hash:
        return False
    return hashlib.sha256(prompt_text.encode("utf-8")).hexdigest() == prompt_hash


def _assemble(
    chat: ChatRequest,
    llm_run: LlmRun | None,
    bundle: EvidenceBundle | None,
) -> ChatRunEvidenceView:
    prompt_text = (llm_run.prompt_text or "") if llm_run else ""
    prompt_hash = (llm_run.prompt_hash or "") if llm_run else ""

    bj: dict = bundle.bundle_json if bundle else {}

    snapshot_data: dict | None = bj.get("snapshot")
    snapshot = (
        SnapshotSummary(
            window=snapshot_data.get("window", ""),
            temperature_avg_c=snapshot_data.get("temperature_avg_c"),
            humidity_avg_pct=snapshot_data.get("humidity_avg_pct"),
            light_avg_lux=snapshot_data.get("light_avg_lux"),
            soil_moisture_avg_pct=snapshot_data.get("soil_moisture_avg_pct"),
        )
        if snapshot_data
        else None
    )

    chunks = [
        ChunkSummary(
            chunk_document_id=c.get("chunk_document_id", ""),
            chunk_kind=c.get("chunk_kind", ""),
            chunk_text=c.get("chunk_text", ""),
            similarity_score=float(c.get("similarity_score", 0.0)),
            rank=int(c.get("rank", 0)),
        )
        for c in bj.get("retrieved_chunks", [])
    ]

    return ChatRunEvidenceView(
        request_id=chat.id,
        plant_id=chat.plant_id,
        question=chat.question,
        intent=chat.status,
        rag_layers=list(bundle.rag_layers) if bundle else [],
        prompt_hash=prompt_hash,
        prompt_text=prompt_text,
        response_text=(llm_run.response_text or "") if llm_run else "",
        model_name=(llm_run.model_name or "") if llm_run else "",
        input_tokens=(llm_run.tokens_in or 0) if llm_run else 0,
        output_tokens=(llm_run.tokens_out or 0) if llm_run else 0,
        latency_ms=(llm_run.latency_ms or 0) if llm_run else 0,
        is_prompt_hash_valid=_check_hash(prompt_text, prompt_hash),
        evidence_hash=bundle.evidence_hash if bundle else None,
        sensor_snapshot=snapshot,
        rule_primary_action=bj.get("rule_primary_action"),
        rule_reason_codes=list(bj.get("rule_reason_codes", [])),
        rule_evidence_facts=dict(bj.get("rule_evidence_facts", {})),
        retrieved_chunks=chunks,
        source_coverage=dict(bj.get("source_coverage", {})),
        created_at=chat.created_at,
    )
