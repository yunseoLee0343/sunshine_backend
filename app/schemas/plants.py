"""Pydantic schemas for the Plant Onboarding API (TICKET-002)."""

import uuid

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# POST /plants/species-candidates  (TICKET-003 — classifier-port backed)
# ---------------------------------------------------------------------------


class SpeciesCandidatesRequest(BaseModel):
    user_id: uuid.UUID
    image_ref: str | None = None  # opaque string — never opened or classified
    locale: str = "ko-KR"
    top_k: int = 3


class SpeciesCandidateItem(BaseModel):
    species_profile_id: uuid.UUID | None = None
    label_ko: str
    label_en: str
    scientific_name: str | None
    confidence: float
    confidence_label: str
    source: str


class SpeciesCandidatesResponse(BaseModel):
    candidates: list[SpeciesCandidateItem]


# ---------------------------------------------------------------------------
# POST /plants
# ---------------------------------------------------------------------------


class CreatePlantRequest(BaseModel):
    user_id: uuid.UUID
    species_profile_id: uuid.UUID
    nickname: str = Field(..., min_length=1)
    room_name: str | None = None

    @field_validator("nickname")
    @classmethod
    def nickname_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("nickname must not be blank")
        return v


class SpeciesBlock(BaseModel):
    korean_name: str
    scientific_name: str | None
    common_name: str | None


class CharacterBlock(BaseModel):
    mood: str
    expression: str
    status_message: str
    reason_code: str


class PlantCard(BaseModel):
    plant_id: uuid.UUID
    user_id: uuid.UUID
    species_profile_id: uuid.UUID | None
    nickname: str
    room_name: str | None
    species: SpeciesBlock | None
    character: CharacterBlock


class CreatePlantResponse(BaseModel):
    plant: PlantCard


# ---------------------------------------------------------------------------
# GET /plants
# ---------------------------------------------------------------------------


class PlantListItem(BaseModel):
    plant_id: uuid.UUID
    nickname: str
    room_name: str | None
    species: SpeciesBlock | None
    character: CharacterBlock | None


class ListPlantsResponse(BaseModel):
    plants: list[PlantListItem]


# ---------------------------------------------------------------------------
# GET /plants/{plant_id}
# ---------------------------------------------------------------------------


class GetPlantResponse(BaseModel):
    plant: PlantCard
