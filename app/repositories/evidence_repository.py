"""EvidenceRepository — TICKET-015. Idempotent store for evidence bundles."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.evidence import ForwardContext
from app.models.evidence_bundle import EvidenceBundle


class EvidenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_hash(self, evidence_hash: str) -> EvidenceBundle | None:
        result = await self.session.execute(
            select(EvidenceBundle).where(EvidenceBundle.evidence_hash == evidence_hash)
        )
        return result.scalar_one_or_none()

    async def save(self, ctx: ForwardContext) -> EvidenceBundle:
        bundle = EvidenceBundle(
            id=uuid.uuid4(),
            evidence_hash=ctx.evidence_hash,
            plant_id=uuid.UUID(ctx.plant_id),
            user_id=uuid.UUID(ctx.user_id),
            question=ctx.question,
            intent=ctx.intent,
            rag_layers=ctx.rag_layers,
            source_coverage=ctx.source_coverage,
            bundle_json=ctx.to_dict(),
            created_at=datetime.now(UTC),
        )
        self.session.add(bundle)
        await self.session.flush()
        return bundle
