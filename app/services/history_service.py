"""GrowthHistoryService — TICKET-FINAL.

Aggregates care_logs, environment_snapshots (hourly), and plant_characters
into a unified newest-first timeline for the history UI.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.care_log import CareLog
from app.models.environment_snapshot import EnvironmentSnapshot
from app.models.plant import Plant
from app.models.plant_character import PlantCharacter
from app.schemas.history import HistoryItem, PlantHistoryResponse

_CARE_ACTION_LABEL = {"watering": "물주기", "note": "노트"}
_MOOD_LABEL = {
    "happy":    "행복해요",
    "thirsty":  "목말라요",
    "sleepy":   "졸려요",
    "stressed": "스트레스를 받아요",
    "neutral":  "보통이에요",
}
_LIMIT_PER_SOURCE = 50


class PlantNotFoundError(Exception):
    pass


def _fmt(val: Decimal | None, unit: str) -> str | None:
    if val is None:
        return None
    return f"{float(val):.1f}{unit}"


def _env_summary(snap: EnvironmentSnapshot) -> str:
    parts = [
        _fmt(snap.temperature_avg_c, "°C"),
        _fmt(snap.soil_moisture_avg_pct, "% 수분"),
        _fmt(snap.humidity_avg_pct, "% 습도"),
        _fmt(snap.light_avg_lux, " lux"),
    ]
    return " · ".join(p for p in parts if p)


class GrowthHistoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_history(
        self,
        plant_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        limit: int = 100,
    ) -> PlantHistoryResponse:
        # Verify ownership
        plant = await self.session.scalar(
            select(Plant).where(
                Plant.id == plant_id,
                Plant.user_id == user_id,
            )
        )
        if plant is None:
            raise PlantNotFoundError(plant_id)

        items: list[HistoryItem] = []

        # ── 1. Care logs ──────────────────────────────────────────────────────
        care_rows = await self.session.scalars(
            select(CareLog)
            .where(CareLog.plant_id == plant_id)
            .order_by(CareLog.acted_at.desc())
            .limit(_LIMIT_PER_SOURCE)
        )
        for log in care_rows:
            items.append(
                HistoryItem(
                    type="care_log",
                    timestamp=log.acted_at,
                    title=_CARE_ACTION_LABEL.get(log.action_type, log.action_type),
                    summary=log.note or "",
                )
            )

        # ── 2. Environment snapshots (hourly only) ────────────────────────────
        env_rows = await self.session.scalars(
            select(EnvironmentSnapshot)
            .where(
                EnvironmentSnapshot.plant_id == plant_id,
                EnvironmentSnapshot.window == "hourly",
            )
            .order_by(EnvironmentSnapshot.window_end.desc())
            .limit(_LIMIT_PER_SOURCE)
        )
        for snap in env_rows:
            summary = _env_summary(snap)
            items.append(
                HistoryItem(
                    type="environment_summary",
                    timestamp=snap.window_end,
                    title="환경 요약",
                    summary=summary,
                )
            )

        # ── 3. Character state history ────────────────────────────────────────
        char_rows = await self.session.scalars(
            select(PlantCharacter)
            .where(PlantCharacter.plant_id == plant_id)
            .order_by(PlantCharacter.created_at.desc())
            .limit(_LIMIT_PER_SOURCE)
        )
        for char in char_rows:
            mood_label = _MOOD_LABEL.get(char.mood, char.mood)
            items.append(
                HistoryItem(
                    type="character_state",
                    timestamp=char.created_at,
                    title=f"기분: {mood_label}",
                    summary=char.status_message,
                )
            )

        # ── Sort newest-first and trim ────────────────────────────────────────
        items.sort(key=lambda x: x.timestamp, reverse=True)

        return PlantHistoryResponse(
            plant_id=plant_id,
            items=items[:limit],
        )
