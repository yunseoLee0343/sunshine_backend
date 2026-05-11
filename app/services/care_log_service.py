"""CareLogService — TICKET-011.

Handles care action logging with atomic character side-effect for watering.

Rules:
  - watering  → insert care_log + insert plant_characters (after_watering) atomically.
  - note       → insert care_log only; character is not touched.
  - No Rule Engine invocation, no home-card refresh, no notifications.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.care_log import CareLog
from app.models.plant_character import PlantCharacter
from app.repositories.care_log_repository import CareLogRepository
from app.repositories.character_repository import CharacterRepository
from app.schemas.care_logs import (
    CareLogCreateResponse,
    CareLogItem,
    CareLogListResponse,
    CareLogRequest,
    CharacterBlock,
)
from app.services.character_state_engine import CharacterStateEngine

_ENGINE = CharacterStateEngine()


def _to_item(log: CareLog) -> CareLogItem:
    return CareLogItem(
        log_id=log.id,
        plant_id=log.plant_id,
        action_type=log.action_type,
        note=log.note,
        acted_at=log.acted_at,
        created_at=log.created_at,
    )


class PlantNotFoundError(Exception):
    """Raised when the plant does not exist or belongs to another user."""


class CareLogService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._log_repo = CareLogRepository(session)
        self._char_repo = CharacterRepository(session)

    async def log_care(self, plant_id: uuid.UUID, req: CareLogRequest) -> CareLogCreateResponse:
        plant = await self._log_repo.get_plant_for_user(plant_id, req.user_id)
        if plant is None:
            raise PlantNotFoundError(plant_id)

        now = datetime.now(UTC)

        log_row = CareLog(
            id=uuid.uuid4(),
            plant_id=plant_id,
            action_type=req.action_type,
            note=req.note,
            acted_at=req.acted_at,
            created_at=now,
        )
        await self._log_repo.create(log_row)

        char_block: CharacterBlock | None = None

        if req.action_type == "watering":
            state = _ENGINE.map("after_watering")
            char_row = PlantCharacter(
                id=uuid.uuid4(),
                plant_id=plant_id,
                mood=state.mood,
                expression=state.expression,
                status_message=state.status_message,
                primary_action=state.primary_action,
                reason_code=state.reason_code,
                created_at=now,
            )
            await self._char_repo.create(char_row)
            char_block = CharacterBlock(
                mood=state.mood,
                expression=state.expression,
                status_message=state.status_message,
                primary_action=state.primary_action,
                reason_code=state.reason_code,
            )

        return CareLogCreateResponse(log=_to_item(log_row), character=char_block)

    async def list_care_logs(self, plant_id: uuid.UUID, user_id: uuid.UUID) -> CareLogListResponse:
        plant = await self._log_repo.get_plant_for_user(plant_id, user_id)
        if plant is None:
            raise PlantNotFoundError(plant_id)

        logs = await self._log_repo.list_for_plant(plant_id)
        return CareLogListResponse(
            plant_id=plant_id,
            logs=[_to_item(log) for log in logs],
        )
