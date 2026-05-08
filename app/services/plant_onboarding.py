"""Plant Onboarding Service (TICKET-002).

Responsibilities:
  - validate user exists
  - validate species exists
  - create plant + initial character in one atomic transaction
  - assemble plant card DTO

Forbidden:
  - sensor aggregation, Rule Engine, LLM, RAG, vision inference
  - background job enqueue
  - any write to sensor_readings / snapshots / chat / llm_runs / evidence / chunks
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plant import Plant
from app.models.plant_character import PlantCharacter
from app.models.user import User
from app.repositories.character_repository import CharacterRepository
from app.repositories.plant_repository import PlantRepository
from app.repositories.species_repository import SpeciesRepository
from app.schemas.plants import (
    CharacterBlock,
    CreatePlantRequest,
    PlantCard,
    PlantListItem,
    SpeciesBlock,
)

# Deterministic initial character state — hardcoded per ticket §11
_INITIAL_MOOD = "neutral"
_INITIAL_EXPRESSION = "normal"
_INITIAL_STATUS_MESSAGE = "새 식물이 등록되었어요."
_INITIAL_REASON_CODE = "onboarding_created"


class PlantOnboardingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.species_repo = SpeciesRepository(session)
        self.plant_repo = PlantRepository(session)
        self.char_repo = CharacterRepository(session)

    # ------------------------------------------------------------------
    # POST /plants
    # ------------------------------------------------------------------

    async def create_plant(self, req: CreatePlantRequest) -> PlantCard:
        # 1. Validate user exists
        user = await self.session.get(User, req.user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="user not found")

        # 2. Validate species exists
        species = await self.species_repo.get_by_id(req.species_profile_id)
        if species is None:
            raise HTTPException(status_code=404, detail="species_profile not found")

        now = datetime.now(UTC)

        # 3. Atomic: plant + initial character in one transaction
        plant = Plant(
            id=uuid.uuid4(),
            user_id=req.user_id,
            species_profile_id=req.species_profile_id,
            nickname=req.nickname,
            room_name=req.room_name,
            created_at=now,
            updated_at=now,
        )
        await self.plant_repo.create(plant)

        character = PlantCharacter(
            id=uuid.uuid4(),
            plant_id=plant.id,
            mood=_INITIAL_MOOD,
            expression=_INITIAL_EXPRESSION,
            status_message=_INITIAL_STATUS_MESSAGE,
            reason_code=_INITIAL_REASON_CODE,
            created_at=now,
        )
        await self.char_repo.create(character)

        await self.session.commit()

        return self._to_plant_card(plant, species, character)

    # ------------------------------------------------------------------
    # GET /plants
    # ------------------------------------------------------------------

    async def list_plants(self, user_id: uuid.UUID) -> list[PlantListItem]:
        plants = await self.plant_repo.list_by_user(user_id)
        items: list[PlantListItem] = []
        for plant in plants:
            species = (
                await self.species_repo.get_by_id(plant.species_profile_id)
                if plant.species_profile_id
                else None
            )
            character = await self.char_repo.get_latest_for_plant(plant.id)
            items.append(self._to_list_item(plant, species, character))
        return items

    # ------------------------------------------------------------------
    # GET /plants/{plant_id}
    # ------------------------------------------------------------------

    async def get_plant(self, plant_id: uuid.UUID, user_id: uuid.UUID) -> PlantCard:
        # Fetch plant regardless of owner (to distinguish 404 vs 403)
        plant = await self.plant_repo.get_by_id(plant_id)
        if plant is None:
            raise HTTPException(status_code=404, detail="plant not found")
        if plant.user_id != user_id:
            raise HTTPException(status_code=403, detail="forbidden")

        species = (
            await self.species_repo.get_by_id(plant.species_profile_id)
            if plant.species_profile_id
            else None
        )
        character = await self.char_repo.get_latest_for_plant(plant.id)
        return self._to_plant_card(plant, species, character)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _species_block(species) -> SpeciesBlock | None:
        if species is None:
            return None
        return SpeciesBlock(
            korean_name=species.korean_name,
            scientific_name=species.scientific_name,
            common_name=species.common_name,
        )

    @staticmethod
    def _character_block(character) -> CharacterBlock | None:
        if character is None:
            return None
        return CharacterBlock(
            mood=character.mood,
            expression=character.expression,
            status_message=character.status_message,
            reason_code=character.reason_code,
        )

    def _to_plant_card(self, plant, species, character) -> PlantCard:
        return PlantCard(
            plant_id=plant.id,
            user_id=plant.user_id,
            species_profile_id=plant.species_profile_id,
            nickname=plant.nickname,
            room_name=plant.room_name,
            species=self._species_block(species),
            character=self._character_block(character),
        )

    def _to_list_item(self, plant, species, character) -> PlantListItem:
        return PlantListItem(
            plant_id=plant.id,
            nickname=plant.nickname,
            room_name=plant.room_name,
            species=self._species_block(species),
            character=self._character_block(character),
        )
