"""Care Action Logging API — TICKET-011.

POST /plants/{plant_id}/care-logs   — create watering or note entry
GET  /plants/{plant_id}/care-logs   — list entries (newest first)
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query

from app.db.session import AsyncSessionLocal
from app.schemas.care_logs import (
    CareLogCreateResponse,
    CareLogListResponse,
    CareLogRequest,
)
from app.services.care_log_service import CareLogService, PlantNotFoundError

router = APIRouter(prefix="/plants", tags=["care-logs"])


@router.post(
    "/{plant_id}/care-logs",
    response_model=CareLogCreateResponse,
    status_code=201,
)
async def create_care_log(
    plant_id: uuid.UUID,
    req: CareLogRequest,
) -> CareLogCreateResponse:
    """Record a care action. Watering also appends a character state entry."""
    async with AsyncSessionLocal() as session:
        svc = CareLogService(session)
        try:
            result = await svc.log_care(plant_id, req)
        except PlantNotFoundError:
            raise HTTPException(status_code=404, detail="plant not found")
        await session.commit()
    return result


@router.get("/{plant_id}/care-logs", response_model=CareLogListResponse)
async def list_care_logs(
    plant_id: uuid.UUID,
    user_id: uuid.UUID = Query(...),
) -> CareLogListResponse:
    """Return care logs for the plant, newest first. 404 if not owned by user."""
    async with AsyncSessionLocal() as session:
        svc = CareLogService(session)
        try:
            return await svc.list_care_logs(plant_id, user_id)
        except PlantNotFoundError:
            raise HTTPException(status_code=404, detail="plant not found")
