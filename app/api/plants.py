"""Plants API router — TICKET-002 Plant Onboarding."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.repositories.species_repository import SpeciesRepository
from app.schemas.plants import (
    CreatePlantRequest,
    CreatePlantResponse,
    GetPlantResponse,
    ListPlantsResponse,
    SpeciesCandidateItem,
    SpeciesCandidatesRequest,
    SpeciesCandidatesResponse,
)
from app.services.plant_onboarding import PlantOnboardingService

router = APIRouter(prefix="/plants", tags=["plants"])


async def get_session():
    """FastAPI dependency: yields an AsyncSession per request."""
    async with AsyncSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# POST /plants/species-candidates
# ---------------------------------------------------------------------------


@router.post("/species-candidates", response_model=SpeciesCandidatesResponse)
async def species_candidates(
    req: SpeciesCandidatesRequest,
    session: AsyncSession = Depends(get_session),
) -> SpeciesCandidatesResponse:
    """Return DB-backed species candidates.

    image_ref is treated as an opaque string — never opened, classified,
    or used for model inference.
    """
    repo = SpeciesRepository(session)
    rows = await repo.list_candidates(limit=20)
    candidates = [
        SpeciesCandidateItem(
            species_profile_id=row.id,
            korean_name=row.korean_name,
            scientific_name=row.scientific_name,
            common_name=row.common_name,
            confidence_label="mock_or_catalog_match",
        )
        for row in rows
    ]
    return SpeciesCandidatesResponse(candidates=candidates)


# ---------------------------------------------------------------------------
# POST /plants
# ---------------------------------------------------------------------------


@router.post("", response_model=CreatePlantResponse, status_code=201)
async def create_plant(
    req: CreatePlantRequest,
    session: AsyncSession = Depends(get_session),
) -> CreatePlantResponse:
    """Create plant + initial character atomically."""
    svc = PlantOnboardingService(session)
    card = await svc.create_plant(req)
    return CreatePlantResponse(plant=card)


# ---------------------------------------------------------------------------
# GET /plants
# ---------------------------------------------------------------------------


@router.get("", response_model=ListPlantsResponse)
async def list_plants(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> ListPlantsResponse:
    """Return all plants belonging to the given user_id."""
    svc = PlantOnboardingService(session)
    plants = await svc.list_plants(user_id)
    return ListPlantsResponse(plants=plants)


# ---------------------------------------------------------------------------
# GET /plants/{plant_id}
# ---------------------------------------------------------------------------


@router.get("/{plant_id}", response_model=GetPlantResponse)
async def get_plant(
    plant_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> GetPlantResponse:
    """Return plant detail; 403 if owned by a different user."""
    svc = PlantOnboardingService(session)
    card = await svc.get_plant(plant_id, user_id)
    return GetPlantResponse(plant=card)
