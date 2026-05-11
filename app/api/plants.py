"""Plants API router — TICKET-002 + TICKET-003 + TICKET-004 + TICKET-018 + TICKET-025."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user, resolve_user_id
from app.db.session import AsyncSessionLocal
from app.models.plant_character import PlantCharacter
from app.repositories.character_repository import CharacterRepository
from app.repositories.plant_repository import PlantRepository
from app.repositories.species_repository import SpeciesRepository
from app.schemas.character_state import (
    CharacterStateResponse,
    CharacterStateUpdateRequest,
)
from app.schemas.chat_answer import ChatAnswerRequest, ChatAnswerResponse
from app.schemas.plants import (
    CharacterBlock,
    CreatePlantRequest,
    CreatePlantResponse,
    GetPlantResponse,
    ListPlantsResponse,
    SpeciesCandidatesRequest,
    SpeciesCandidatesResponse,
)
from app.services.character_state_engine import (
    CharacterStateEngine,
    UnknownConditionError,
)
from app.services.chat_orchestrator import ChatOrchestrator
from app.services.evidence_builder import PlantNotFoundError
from app.services.plant_onboarding import PlantOnboardingService
from app.services.species_candidate_service import SpeciesCandidateService
from app.vision.mock_species_classifier import MockSpeciesClassifier
from app.vision.species_classifier import SpeciesClassifierPort

router = APIRouter(prefix="/plants", tags=["plants"])

# Pure deterministic engine — instantiated once at import time.
_character_engine = CharacterStateEngine()

# Lightweight, stateless mock — instantiated once at import time.
# Real model loading is forbidden in this ticket.
_mock_classifier = MockSpeciesClassifier()

_orchestrator = ChatOrchestrator()


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
    user_id: uuid.UUID | None = Query(default=None),
    current_user: CurrentUser | None = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ListPlantsResponse:
    """Return all plants belonging to the user.

    User identity: X-User-Id header (preferred) or ?user_id= query param.
    """
    uid = resolve_user_id(user_id, current_user)
    svc = PlantOnboardingService(session)
    plants = await svc.list_plants(uid)
    return ListPlantsResponse(plants=plants)


# ---------------------------------------------------------------------------
# GET /plants/{plant_id}
# ---------------------------------------------------------------------------


@router.get("/{plant_id}", response_model=GetPlantResponse)
async def get_plant(
    plant_id: uuid.UUID,
    user_id: uuid.UUID | None = Query(default=None),
    current_user: CurrentUser | None = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> GetPlantResponse:
    """Return plant detail; 403 if owned by a different user.

    User identity: X-User-Id header (preferred) or ?user_id= query param.
    """
    uid = resolve_user_id(user_id, current_user)
    svc = PlantOnboardingService(session)
    card = await svc.get_plant(plant_id, uid)
    return GetPlantResponse(plant=card)


# ---------------------------------------------------------------------------
# POST /plants/{plant_id}/character-state  (TICKET-004 — internal/dev)
# ---------------------------------------------------------------------------


@router.post(
    "/{plant_id}/character-state",
    response_model=CharacterStateResponse,
)
async def update_character_state(
    plant_id: uuid.UUID,
    req: CharacterStateUpdateRequest,
    current_user: CurrentUser | None = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CharacterStateResponse:
    """Append a deterministic character state for the plant.

    Caller supplies only ``user_id`` + ``condition``; the engine resolves
    mood / expression / status_message / primary_action / reason_code. Any
    extra field on the request is rejected by Pydantic ``extra="forbid"``.

    User identity: X-User-Id header (preferred) or request body user_id.
    """
    effective_uid = current_user.user_id if current_user is not None else req.user_id
    plant_repo = PlantRepository(session)
    plant = await plant_repo.get_by_id(plant_id)
    if plant is None:
        raise HTTPException(status_code=404, detail="plant not found")
    if plant.user_id != effective_uid:
        raise HTTPException(status_code=403, detail="forbidden")

    try:
        state = _character_engine.map(req.condition)
    except UnknownConditionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    char_repo = CharacterRepository(session)
    row = PlantCharacter(
        id=uuid.uuid4(),
        plant_id=plant_id,
        mood=state.mood,
        expression=state.expression,
        status_message=state.status_message,
        primary_action=state.primary_action,
        reason_code=state.reason_code,
        created_at=datetime.now(UTC),
    )
    await char_repo.create(row)
    await session.commit()

    return CharacterStateResponse(
        character=CharacterBlock(
            mood=state.mood,
            expression=state.expression,
            status_message=state.status_message,
            primary_action=state.primary_action,
            reason_code=state.reason_code,
        )
    )


# ---------------------------------------------------------------------------
# POST /plants/{plant_id}/chat  (TICKET-018)
# ---------------------------------------------------------------------------


@router.post(
    "/{plant_id}/chat",
    response_model=ChatAnswerResponse,
    status_code=201,
)
async def chat_care_answer(
    plant_id: uuid.UUID,
    req: ChatAnswerRequest,
    current_user: CurrentUser | None = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChatAnswerResponse:
    """Run the full plant care chat pipeline and return a structured answer.

    Idempotent: re-submitting the same request_id returns the cached answer.
    Returns 404 when the plant_id does not exist.

    User identity: X-User-Id header (preferred) or request body user_id.
    """
    effective_uid = current_user.user_id if current_user is not None else req.user_id
    try:
        resp = await _orchestrator.run(
            session,
            plant_id=plant_id,
            user_id=effective_uid,
            question=req.question,
            request_id=req.request_id,
            image_uri=req.image_uri,
            audio_uri=req.audio_uri,
        )
        await session.commit()
        return resp
    except PlantNotFoundError:
        raise HTTPException(status_code=404, detail="plant not found")
