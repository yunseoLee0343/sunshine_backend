"""Companion recommendation API — TICKET-021.

GET /plants/{plant_id}/companion-recommendations
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.schemas.companion_recommendation import CompanionRecommendationResponse
from app.services.companion_recommendation_service import (
    CompanionRecommendationService,
    PlantOwnershipError,
)
from app.services.evidence_builder import PlantNotFoundError

router = APIRouter(prefix="/plants", tags=["companion"])


async def _get_session():
    async with AsyncSessionLocal() as session:
        yield session


@router.get(
    "/{plant_id}/companion-recommendations",
    response_model=CompanionRecommendationResponse,
)
async def companion_recommendations(
    plant_id: uuid.UUID,
    user_id: uuid.UUID,
    top_k: int = Query(default=5, ge=1, le=20),
    session: AsyncSession = Depends(_get_session),
) -> CompanionRecommendationResponse:
    """Return compatible companion plant candidates for the given plant.

    Ownership is verified: user_id must match plant.user_id.
    Only compatible candidates (score >= 0.5, assessed_dimensions > 0) are
    returned. Sorted by compatibility score desc, then common_name asc.
    """
    svc = CompanionRecommendationService(session)
    try:
        return await svc.recommend(plant_id, user_id, top_k=top_k)
    except PlantNotFoundError:
        raise HTTPException(status_code=404, detail="plant not found")
    except PlantOwnershipError:
        raise HTTPException(status_code=403, detail="forbidden")
