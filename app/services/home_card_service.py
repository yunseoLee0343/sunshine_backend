"""HomeCardService — TICKET-009.

Assembles PlantHomeCard responses by combining:
  - plant + species metadata (HomeCardRepository)
  - latest character state  (HomeCardRepository)
  - latest sensor snapshot  (RuleInputRepository → LatestSnapshot)
  - Rule Engine output      (RuleEngine, always called — no manual threshold checks)

Strictly read-only: no DB writes, no commits, no flushes.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plant import Plant
from app.repositories.home_card_repository import HomeCardRepository
from app.repositories.rule_input_repository import RuleInputRepository
from app.rules.types import LatestSnapshot, SpeciesThresholds
from app.schemas.home import (
    CharacterSummary,
    EnvironmentBlock,
    HomeResponse,
    PlantHomeCard,
)
from app.services.rule_engine import RuleEngine

_DEFAULT_CHARACTER = CharacterSummary(
    mood="neutral",
    expression="normal",
    status_message="새 식물이 등록되었어요.",
    primary_action="none",
    reason_code="onboarding_created",
)

_ENGINE = RuleEngine()


class HomeCardService:
    def __init__(self, session: AsyncSession, *, now: datetime | None = None) -> None:
        self._session = session
        self._now = now or datetime.now(UTC)
        self._home_repo = HomeCardRepository(session)
        self._rule_repo = RuleInputRepository(session)

    async def _build_card(self, plant: Plant) -> PlantHomeCard:
        now = self._now

        # Species name ---------------------------------------------------------
        species_name: str | None = None
        if plant.species_profile_id:
            sp = await self._home_repo.get_species_profile(plant.species_profile_id)
            species_name = sp.korean_name if sp else None

        # Character state (in-memory default when no history row) ---------------
        char_row = await self._home_repo.get_latest_character(plant.id)
        character = (
            CharacterSummary(
                mood=char_row.mood,
                expression=char_row.expression,
                status_message=char_row.status_message,
                primary_action=char_row.primary_action,
                reason_code=char_row.reason_code,
            )
            if char_row is not None
            else _DEFAULT_CHARACTER
        )

        # Rule Engine inputs ---------------------------------------------------
        thresholds: SpeciesThresholds = (
            (await self._rule_repo.get_thresholds(plant.species_profile_id)) if plant.species_profile_id else None
        ) or SpeciesThresholds()

        since = now - timedelta(days=7)
        care_logs = await self._rule_repo.get_recent_care_logs(plant.id, since=since, now=now)
        latest_snap = await self._rule_repo.get_latest_snapshot(plant.id, before=now)

        # Environment block (null when no DB snapshot) -------------------------
        environment: EnvironmentBlock | None = (
            EnvironmentBlock(
                soil_moisture_avg_pct=latest_snap.soil_moisture_avg_pct,
                light_avg_lux=latest_snap.light_avg_lux,
                humidity_avg_pct=latest_snap.humidity_avg_pct,
                temperature_avg_c=latest_snap.temperature_avg_c,
            )
            if latest_snap is not None
            else None
        )

        # Rule Engine (always invoked — never skip or short-circuit) -----------
        rule_result = _ENGINE.evaluate(
            plant_id=plant.id,
            thresholds=thresholds,
            snapshot=latest_snap or LatestSnapshot(),
            care_logs=care_logs,
            now=now,
        )

        return PlantHomeCard(
            plant_id=plant.id,
            nickname=plant.nickname,
            room_name=plant.room_name,
            species_name=species_name,
            character=character,
            environment=environment,
            today_recommended_action=rule_result.primary_action,
            care_status=rule_result.care_status,
        )

    async def get_home(self, user_id: uuid.UUID) -> HomeResponse:
        plants = await self._home_repo.list_plants_by_user(user_id)
        cards = [await self._build_card(p) for p in plants]
        return HomeResponse(user_id=user_id, plants=cards)

    async def get_plant_card(self, plant_id: uuid.UUID, user_id: uuid.UUID) -> PlantHomeCard | None:
        """Return None when plant doesn't exist or belongs to another user."""
        plant = await self._home_repo.get_plant_for_user(plant_id, user_id)
        if plant is None:
            return None
        return await self._build_card(plant)
