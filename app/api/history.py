"""Growth History API — TICKET-FINAL.

GET /plants/{plant_id}/history   — unified care + environment + character timeline
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import CurrentUser, get_current_user, resolve_user_id
from app.db.session import AsyncSessionLocal
from app.schemas.history import PlantHistoryResponse
from app.services.history_service import GrowthHistoryService, PlantNotFoundError

router = APIRouter(prefix="/plants", tags=["plants"])


@router.get("/{plant_id}/history", response_model=PlantHistoryResponse)
async def get_plant_history(
    plant_id: uuid.UUID,
    user_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> PlantHistoryResponse:
    """Return unified growth history (care logs + environment snapshots + character states).

    Items are sorted newest-first. Up to `limit` total items are returned
    (default 100, max 200).

    User identity: X-User-Id header (preferred) or ?user_id= query param.
    """
    uid = resolve_user_id(user_id, current_user)
    async with AsyncSessionLocal() as session:
        svc = GrowthHistoryService(session)
        try:
            return await svc.get_history(plant_id, uid, limit=limit)
        except PlantNotFoundError:
            raise HTTPException(status_code=404, detail="plant not found")
