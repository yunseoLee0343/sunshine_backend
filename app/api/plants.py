"""Plants API router — TICKET-002 + TICKET-003."""

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
    SpeciesCandidatesRequest,
    SpeciesCandidatesResponse,
)
from app.services.plant_onboarding import PlantOnboardingService
from app.services.species_candidate_service import SpeciesCandidateService
from app.vision.mock_species_classifier import MockSpeciesClassifier
from app.vision.species_classifier import SpeciesClassifierPort

router = APIRouter(prefix="/plants", tags=["plants"])

# Lightweight, stateless mock — instantiated once at import time.
# Real model loading is forbidden in this ticket.
_mock_classifier = MockSpeciesClassifier()


async def get_session():
    """FastAPI dependency: yields an AsyncSession per request."""
    async with AsyncSessionLocal() as session:
        yield session


def get_species_classifier() -> SpeciesClassifierPort:
    """FastAPI dependency: yields the configured species classifier port.

    Override this in tests to inject a fake classifier.
    """
    return _mock_classifier


# ---------------------------------------------------------------------------
# POST /plants/species-candidates  (TICKET-003)
# ---------------------------------------------------------------------------


@router.post("/species-candidates", response_model=SpeciesCandidatesResponse)
async def species_candidates(
    req: SpeciesCandidatesRequest,
    session: AsyncSession = Depends(get_session),
    classifier: SpeciesClassifierPort = Depends(get_species_classifier),
) -> SpeciesCandidatesResponse:
    """Return species candidates produced by the classifier port.

    image_ref is treated as an opaque string — never opened, fetched, or
    decoded. Each candidate is optionally resolved to an existing row in
    species_profiles; a missing match yields species_profile_id = null.
    """
    repo = SpeciesRepository(session)
    svc = SpeciesCandidateService(classifier=classifier, species_repo=repo)
    return await svc.list_candidates(
        image_ref=req.image_ref,
        locale=req.locale,
        top_k=req.top_k,
    )


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
