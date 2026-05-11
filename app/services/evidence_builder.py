"""EvidenceBuilderService — TICKET-015.

Aggregates data from prior tickets into a ForwardContext bundle:
  - TICKET-004/011: latest PlantCharacter + recent CareLog rows
  - TICKET-005/010: latest EnvironmentSnapshot
  - TICKET-008:     RuleEngine evaluation (pure, no DB write)
  - TICKET-014C:    RetrievalResultChunk rows (if retrieval_run_id supplied)

No LLM, no prompt construction, no answer text generated.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.evidence import (
    CareLogEvidence,
    CharacterEvidence,
    ChunkEvidence,
    ForwardContext,
    SnapshotEvidence,
)
from app.domain.retrieval import RAG_LAYER_TO_CHUNK_KINDS
from app.models.care_log import CareLog
from app.models.environment_snapshot import EnvironmentSnapshot
from app.models.plant import Plant
from app.models.plant_character import PlantCharacter
from app.models.retrieval_result_chunk import RetrievalResultChunk
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.rule_input_repository import RuleInputRepository
from app.rules.types import LatestSnapshot, SpeciesThresholds
from app.schemas.evidence_bundle import EvidenceBuildRequest
from app.services.rule_engine import RuleEngine

_RULE_ENGINE = RuleEngine()
_CARE_LOG_LOOKBACK_DAYS = 14
_RECENT_CARE_LOG_LIMIT = 5


class PlantNotFoundError(Exception):
    pass


class EvidenceBuilderService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._rule_repo = RuleInputRepository(session)
        self._evidence_repo = EvidenceRepository(session)

    async def build(self, req: EvidenceBuildRequest) -> tuple[ForwardContext, bool]:
        """Return (ForwardContext, from_cache)."""
        now = datetime.now(UTC)

        # ---- gather components -------------------------------------------
        plant = await self.session.get(Plant, req.plant_id)
        if plant is None:
            raise PlantNotFoundError(f"plant {req.plant_id} not found")

        character = await self._load_character(req.plant_id)
        snapshot = await self._load_snapshot(req.plant_id)
        care_logs = await self._load_care_logs(req.plant_id, now)
        rule_result = await self._run_rules(plant, now)
        chunks = await self._load_chunks(req.retrieval_run_id)
        source_coverage = _compute_coverage(req.rag_layers, chunks)

        # ---- build context -----------------------------------------------
        ctx = ForwardContext.build(
            plant_id=req.plant_id,
            user_id=req.user_id,
            question=req.question,
            intent=req.intent,
            rag_layers=list(req.rag_layers),
            character=character,
            snapshot=snapshot,
            recent_care_logs=care_logs,
            rule_evidence_facts=rule_result["evidence_facts"],
            rule_reason_codes=rule_result["reason_codes"],
            rule_primary_action=rule_result["primary_action"],
            retrieved_chunks=chunks,
            source_coverage=source_coverage,
            visual_facts=list(req.visual_facts),
        )

        # ---- idempotency --------------------------------------------------
        existing = await self._evidence_repo.get_by_hash(ctx.evidence_hash)
        if existing is not None:
            return ctx, True

        await self._evidence_repo.save(ctx)
        return ctx, False

    # ---------------------------------------------------------------------- helpers

    async def _load_character(self, plant_id: uuid.UUID) -> CharacterEvidence | None:
        result = await self.session.execute(
            select(PlantCharacter)
            .where(PlantCharacter.plant_id == plant_id)
            .order_by(PlantCharacter.created_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return CharacterEvidence(
            mood=row.mood,
            expression=row.expression,
            status_message=row.status_message,
            primary_action=row.primary_action,
            reason_code=row.reason_code,
        )

    async def _load_snapshot(self, plant_id: uuid.UUID) -> SnapshotEvidence | None:
        result = await self.session.execute(
            select(EnvironmentSnapshot)
            .where(EnvironmentSnapshot.plant_id == plant_id)
            .order_by(EnvironmentSnapshot.window_end.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return SnapshotEvidence(
            window=row.window,
            temperature_avg_c=float(row.temperature_avg_c) if row.temperature_avg_c is not None else None,
            humidity_avg_pct=float(row.humidity_avg_pct) if row.humidity_avg_pct is not None else None,
            light_avg_lux=float(row.light_avg_lux) if row.light_avg_lux is not None else None,
            soil_moisture_avg_pct=float(row.soil_moisture_avg_pct) if row.soil_moisture_avg_pct is not None else None,
        )

    async def _load_care_logs(self, plant_id: uuid.UUID, now: datetime) -> list[CareLogEvidence]:
        since = now - timedelta(days=_CARE_LOG_LOOKBACK_DAYS)
        result = await self.session.execute(
            select(CareLog)
            .where(CareLog.plant_id == plant_id, CareLog.acted_at >= since)
            .order_by(CareLog.acted_at.desc())
            .limit(_RECENT_CARE_LOG_LIMIT)
        )
        return [
            CareLogEvidence(
                action_type=row.action_type,
                note=row.note,
                acted_at=row.acted_at.isoformat(),
            )
            for row in result.scalars().all()
        ]

    async def _run_rules(self, plant: Plant, now: datetime) -> dict:
        """Run the rule engine; return a plain dict of evidence fields.
        Gracefully returns empty values when species/snapshot data is absent.
        """
        thresholds: SpeciesThresholds | None = None
        if plant.species_profile_id is not None:
            thresholds = await self._rule_repo.get_thresholds(plant.species_profile_id)
        if thresholds is None:
            thresholds = SpeciesThresholds(
                water_min_pct=None,
                water_max_pct=None,
                light_min_lux=None,
                light_max_lux=None,
                humidity_min_pct=None,
                humidity_max_pct=None,
                temperature_min_c=None,
                temperature_max_c=None,
            )

        snapshot = await self._rule_repo.get_latest_snapshot(plant.id, before=now)
        if snapshot is None:
            snapshot = LatestSnapshot(
                soil_moisture_avg_pct=None,
                light_avg_lux=None,
                humidity_avg_pct=None,
                temperature_avg_c=None,
            )

        since = now - timedelta(days=_CARE_LOG_LOOKBACK_DAYS)
        care_logs = await self._rule_repo.get_recent_care_logs(plant.id, since=since, now=now)

        result = _RULE_ENGINE.evaluate(
            plant_id=plant.id,
            thresholds=thresholds,
            snapshot=snapshot,
            care_logs=care_logs,
            now=now,
        )
        return {
            "evidence_facts": result.evidence_facts,
            "reason_codes": result.reason_codes,
            "primary_action": result.primary_action,
        }

    async def _load_chunks(self, retrieval_run_id: uuid.UUID | None) -> list[ChunkEvidence]:
        if retrieval_run_id is None:
            return []
        result = await self.session.execute(
            select(RetrievalResultChunk)
            .where(RetrievalResultChunk.run_id == retrieval_run_id)
            .order_by(RetrievalResultChunk.rank)
        )
        return [
            ChunkEvidence(
                chunk_document_id=str(row.chunk_document_id),
                plant_knowledge_id=str(row.plant_knowledge_id),
                chunk_kind=row.chunk_kind,
                chunk_text=row.chunk_text,
                similarity_score=row.similarity_score,
                rank=row.rank,
            )
            for row in result.scalars().all()
        ]


def _compute_coverage(rag_layers: list[str], chunks: list[ChunkEvidence]) -> dict[str, bool]:
    retrieved_kinds = {c.chunk_kind for c in chunks}
    coverage: dict[str, bool] = {}
    for layer in rag_layers:
        expected = set(RAG_LAYER_TO_CHUNK_KINDS.get(layer, ()))
        coverage[layer] = bool(expected & retrieved_kinds)
    return coverage
