"""Plant Environment Detail API — TICKET-010.

GET /plants/{plant_id}/environment?user_id=<uuid>
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query

from app.db.session import AsyncSessionLocal
from app.schemas.environment_detail import EnvironmentDetailResponse
from app.services.environment_detail_service import EnvironmentDetailService

router = APIRouter(prefix="/plants", tags=["environment"])


@router.get("/{plant_id}/environment", response_model=EnvironmentDetailResponse)
async def get_plant_environment(
    plant_id: uuid.UUID,
    user_id: uuid.UUID = Query(...),
) -> EnvironmentDetailResponse:
    """Return pre-computed snapshot summaries and character explanation.

    Returns 404 when the plant does not exist or belongs to another user.
    Read-only: no snapshot generation, no rule engine, no LLM.
    """
    async with AsyncSessionLocal() as session:
        svc = EnvironmentDetailService(session)
        result = await svc.get_detail(plant_id, user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="plant not found")
    return result
