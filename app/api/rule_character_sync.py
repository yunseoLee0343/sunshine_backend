"""Internal rule-character sync endpoint — TICKET-008.5.

POST /internal/rule-character-sync/{plant_id}

Runs the Rule Engine for the plant and immediately syncs the result
to plant_characters. Intended for integration testing and manual
triggering; not part of the public API contract.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.plant import Plant
from app.repositories.rule_input_repository import RuleInputRepository
from app.rules.types import LatestSnapshot, SpeciesThresholds
from app.services.rule_character_sync import RuleCharacterSyncService
from app.services.rule_engine import RuleEngine

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/rule-character-sync/{plant_id}", status_code=200)
async def sync_rule_to_character(plant_id: uuid.UUID) -> JSONResponse:
    now = datetime.now(UTC)

    async with AsyncSessionLocal() as session:
        plant = await session.get(Plant, plant_id)
        if plant is None:
            raise HTTPException(status_code=404, detail="plant not found")

        repo = RuleInputRepository(session)

        thresholds = (
            await repo.get_thresholds(plant.species_profile_id)
            if plant.species_profile_id
            else None
        ) or SpeciesThresholds()

        snapshot = await repo.get_latest_snapshot(plant_id, before=now) or LatestSnapshot()
        since = now - timedelta(days=7)
        care_logs = await repo.get_recent_care_logs(plant_id, since=since, now=now)

        rule_result = RuleEngine().evaluate(
            plant_id=plant_id,
            thresholds=thresholds,
            snapshot=snapshot,
            care_logs=care_logs,
            now=now,
        )

        svc = RuleCharacterSyncService(session)
        row = await svc.sync(rule_result, now=now)
        await session.commit()

    return JSONResponse(content={
        "id": str(row.id),
        "plant_id": str(row.plant_id),
        "mood": row.mood,
        "expression": row.expression,
        "status_message": row.status_message,
        "primary_action": row.primary_action,
        "reason_code": row.reason_code,
        "created_at": row.created_at.isoformat(),
        "rule_care_status": rule_result.care_status,
        "rule_primary_action": rule_result.primary_action,
    })
