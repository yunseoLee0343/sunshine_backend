"""Pydantic schemas for the Plant Onboarding API (TICKET-002)."""

import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# POST /plants/species-candidates  (TICKET-003 — classifier-port backed)
# ---------------------------------------------------------------------------


class SpeciesCandidatesRequest(BaseModel):
    user_id: uuid.UUID
    image_ref: str | None = None  # opaque string — never opened or classified
    locale: str = "ko-KR"
    top_k: int = 3


_EXAMPLE_PLANT_ID = "b2c3d4e5-f6a7-8901-bcde-f12345678901"
_EXAMPLE_USER_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
_EXAMPLE_SPECIES_ID = "c3d4e5f6-a7b8-9012-cdef-123456789012"
_EXAMPLE_CHARACTER = {
    "mood": "neutral",
    "expression": "normal",
    "status_message": "새 식물이 등록되었어요.",
    "primary_action": "none",
    "reason_code": "onboarding_created",
}
_EXAMPLE_SPECIES = {
    "korean_name": "몬스테라",
    "scientific_name": "Monstera deliciosa",
    "common_name": "Monstera",
}
_EXAMPLE_PLANT_CARD = {
    "plant_id": _EXAMPLE_PLANT_ID,
    "user_id": _EXAMPLE_USER_ID,
    "species_profile_id": _EXAMPLE_SPECIES_ID,
    "nickname": "초록이",
    "room_name": "거실",
    "species": _EXAMPLE_SPECIES,
    "character": _EXAMPLE_CHARACTER,
}


class SpeciesCandidateItem(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "species_profile_id": _EXAMPLE_SPECIES_ID,
                "label_ko": "몬스테라",
                "label_en": "Monstera",
                "scientific_name": "Monstera deliciosa",
                "confidence": 0.92,
                "confidence_label": "high",
                "source": "mock",
            }
        }
    )

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
    primary_action: str = "none"
    reason_code: str


class PlantCard(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": _EXAMPLE_PLANT_CARD})

    plant_id: uuid.UUID
    user_id: uuid.UUID
    species_profile_id: uuid.UUID | None
    nickname: str
    room_name: str | None
    species: SpeciesBlock | None
    character: CharacterBlock


class CreatePlantResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"plant": _EXAMPLE_PLANT_CARD}})

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
    model_config = ConfigDict(json_schema_extra={"example": {"plants": []}})

    plants: list[PlantListItem]


# ---------------------------------------------------------------------------
# GET /plants/{plant_id}
# ---------------------------------------------------------------------------


class GetPlantResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"plant": _EXAMPLE_PLANT_CARD}})

    plant: PlantCard
