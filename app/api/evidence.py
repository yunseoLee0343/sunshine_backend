"""POST /evidence/build — TICKET-015. Internal endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.db.session import AsyncSessionLocal
from app.schemas.evidence_bundle import EvidenceBuildRequest, EvidenceBundleResponse
from app.services.evidence_builder import EvidenceBuilderService, PlantNotFoundError

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.post("/build", response_model=EvidenceBundleResponse)
async def build_evidence(body: EvidenceBuildRequest) -> EvidenceBundleResponse:
    async with AsyncSessionLocal() as session:
        svc = EvidenceBuilderService(session)
        try:
            ctx, from_cache = await svc.build(body)
        except PlantNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        await session.commit()

    return EvidenceBundleResponse(
        evidence_hash=ctx.evidence_hash,
        plant_id=ctx.plant_id,
        user_id=ctx.user_id,
        question=ctx.question,
        intent=ctx.intent,
        rag_layers=ctx.rag_layers,
        character=ctx.character,
        snapshot=ctx.snapshot,
        recent_care_logs=ctx.recent_care_logs,
        rule_evidence_facts=ctx.rule_evidence_facts,
        rule_reason_codes=ctx.rule_reason_codes,
        rule_primary_action=ctx.rule_primary_action,
        retrieved_chunks=ctx.retrieved_chunks,
        source_coverage=ctx.source_coverage,
        from_cache=from_cache,
    )
