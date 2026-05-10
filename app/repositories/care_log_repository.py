"""CareLogRepository — TICKET-011.

Handles care_logs persistence and plant ownership verification.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.care_log import CareLog
from app.models.plant import Plant


class CareLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_plant_for_user(
        self, plant_id: uuid.UUID, user_id: uuid.UUID
    ) -> Plant | None:
        """Return plant only when it belongs to the requesting user."""
        result = await self.session.execute(
            select(Plant).where(
                Plant.id == plant_id,
                Plant.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, log: CareLog) -> CareLog:
        self.session.add(log)
        await self.session.flush()
        return log

    async def list_for_plant(
        self, plant_id: uuid.UUID, *, limit: int = 50
    ) -> list[CareLog]:
        """Return care logs in descending acted_at order (newest first)."""
        result = await self.session.execute(
            select(CareLog)
            .where(CareLog.plant_id == plant_id)
            .order_by(CareLog.acted_at.desc(), CareLog.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
