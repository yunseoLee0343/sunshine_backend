"""RuleCharacterSyncService — TICKET-008.5.

Orchestrates: RuleEngineResult → Condition → CharacterState → DB row.
Always appends a new plant_characters row; never updates or deletes.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plant_character import PlantCharacter
from app.repositories.character_repository import CharacterRepository
from app.rules.schemas import RuleEngineResult
from app.services.character_state_engine import CharacterStateEngine
from app.services.rule_to_character_mapper import map_to_condition


class RuleCharacterSyncService:
    """Syncs a RuleEngineResult to an append-only character history row."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._char_engine = CharacterStateEngine()
        self._repo = CharacterRepository(session)

    async def sync(
        self,
        result: RuleEngineResult,
        *,
        now: datetime | None = None,
    ) -> PlantCharacter:
        condition = map_to_condition(result)
        state = self._char_engine.map(condition)

        row = PlantCharacter(
            plant_id=result.plant_id,
            mood=state.mood,
            expression=state.expression,
            status_message=state.status_message,
            primary_action=state.primary_action,
            reason_code=state.reason_code,
            created_at=now or datetime.now(UTC),
        )
        await self._repo.create(row)
        return row
