"""Home Plant Card API — TICKET-009.

GET /home?user_id=<uuid>            — all cards for a user
GET /plants/{plant_id}/card?user_id=<uuid>  — single plant card (auth-gated)
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.schemas.home import HomeResponse, PlantHomeCard
from app.services.home_card_service import HomeCardService

router = APIRouter(tags=["home"])


@router.get("/home", response_model=HomeResponse)
async def get_home(user_id: uuid.UUID = Query(...)) -> HomeResponse:
    """Return summary cards for every plant owned by user_id."""
    async with AsyncSessionLocal() as session:
        svc = HomeCardService(session)
        return await svc.get_home(user_id)


@router.get("/plants/{plant_id}/card", response_model=PlantHomeCard)
async def get_plant_card(
    plant_id: uuid.UUID,
    user_id: uuid.UUID = Query(...),
) -> PlantHomeCard:
    """Return the home card for a single plant.

    Returns 404 when the plant does not exist or belongs to another user
    (no information leak about other users' plants).
    """
    async with AsyncSessionLocal() as session:
        svc = HomeCardService(session)
        card = await svc.get_plant_card(plant_id, user_id)
    if card is None:
        raise HTTPException(status_code=404, detail="plant not found")
    return card
