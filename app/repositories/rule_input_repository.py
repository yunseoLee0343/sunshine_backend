"""RuleInputRepository — TICKET-008.

Loads species thresholds, latest snapshot, and recent care logs from the DB
and converts them to pure-data rule input types. No judgment logic here.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.care_log import CareLog
from app.models.environment_snapshot import EnvironmentSnapshot
from app.models.species_profile import SpeciesProfile
from app.rules.types import LatestSnapshot, RecentCareLog, SpeciesThresholds


class RuleInputRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_thresholds(self, species_profile_id: uuid.UUID) -> SpeciesThresholds | None:
        row = await self.session.get(SpeciesProfile, species_profile_id)
        if row is None:
            return None
        return SpeciesThresholds(
            water_min_pct=row.water_min_pct,
            water_max_pct=row.water_max_pct,
            light_min_lux=row.light_min_lux,
            light_max_lux=row.light_max_lux,
            humidity_min_pct=row.humidity_min_pct,
            humidity_max_pct=row.humidity_max_pct,
            temperature_min_c=row.temperature_min_c,
            temperature_max_c=row.temperature_max_c,
        )

    async def get_latest_snapshot(
        self, plant_id: uuid.UUID, before: datetime
    ) -> LatestSnapshot | None:
        result = await self.session.execute(
            select(EnvironmentSnapshot)
            .where(
                EnvironmentSnapshot.plant_id == plant_id,
                EnvironmentSnapshot.window == "latest",
                EnvironmentSnapshot.window_end <= before,
            )
            .order_by(EnvironmentSnapshot.window_end.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return LatestSnapshot(
            soil_moisture_avg_pct=float(row.soil_moisture_avg_pct)
            if row.soil_moisture_avg_pct is not None
            else None,
            light_avg_lux=float(row.light_avg_lux) if row.light_avg_lux is not None else None,
            humidity_avg_pct=float(row.humidity_avg_pct)
            if row.humidity_avg_pct is not None
            else None,
            temperature_avg_c=float(row.temperature_avg_c)
            if row.temperature_avg_c is not None
            else None,
        )

    async def get_recent_care_logs(
        self, plant_id: uuid.UUID, since: datetime, now: datetime
    ) -> list[RecentCareLog]:
        result = await self.session.execute(
            select(CareLog).where(
                CareLog.plant_id == plant_id,
                CareLog.acted_at >= since,
                CareLog.acted_at <= now,
            )
        )
        logs = result.scalars().all()
        return [
            RecentCareLog(
                action_type=log.action_type,
                hours_ago=(now - log.acted_at).total_seconds() / 3600,
            )
            for log in logs
        ]
