"""PlantKnowledgeRepository — TICKET-014A.

Read-only lookup repository. No search-by-keyword, no vector queries,
no embedding generation.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plant_care_requirement import PlantCareRequirement
from app.models.plant_knowledge_entry import PlantKnowledgeEntry
from app.models.plant_knowledge_source import PlantKnowledgeSource
from app.models.plant_pest_reference import PlantPestReference
from app.models.plant_placement import PlantPlacement
from app.models.plant_seasonal_watering import PlantSeasonalWatering
from app.models.plant_visual_trait import PlantVisualTrait


class PlantKnowledgeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------ entry

    async def get_entry_by_id(self, entry_id: uuid.UUID) -> PlantKnowledgeEntry | None:
        return await self.session.get(PlantKnowledgeEntry, entry_id)

    async def get_entry_by_nongsaro_id(
        self, nongsaro_id: str
    ) -> PlantKnowledgeEntry | None:
        result = await self.session.execute(
            select(PlantKnowledgeEntry).where(
                PlantKnowledgeEntry.nongsaro_id == nongsaro_id
            )
        )
        return result.scalar_one_or_none()

    async def get_entry_by_scientific_name(
        self, scientific_name: str
    ) -> PlantKnowledgeEntry | None:
        result = await self.session.execute(
            select(PlantKnowledgeEntry).where(
                PlantKnowledgeEntry.scientific_name == scientific_name
            )
        )
        return result.scalar_one_or_none()

    # ---------------------------------------------------------------- children

    async def get_care_requirement(
        self, entry_id: uuid.UUID
    ) -> PlantCareRequirement | None:
        result = await self.session.execute(
            select(PlantCareRequirement).where(
                PlantCareRequirement.entry_id == entry_id
            )
        )
        return result.scalar_one_or_none()

    async def get_seasonal_watering(
        self, entry_id: uuid.UUID
    ) -> PlantSeasonalWatering | None:
        result = await self.session.execute(
            select(PlantSeasonalWatering).where(
                PlantSeasonalWatering.entry_id == entry_id
            )
        )
        return result.scalar_one_or_none()

    async def get_pest_reference(
        self, entry_id: uuid.UUID
    ) -> PlantPestReference | None:
        result = await self.session.execute(
            select(PlantPestReference).where(
                PlantPestReference.entry_id == entry_id
            )
        )
        return result.scalar_one_or_none()

    async def get_visual_trait(self, entry_id: uuid.UUID) -> PlantVisualTrait | None:
        result = await self.session.execute(
            select(PlantVisualTrait).where(PlantVisualTrait.entry_id == entry_id)
        )
        return result.scalar_one_or_none()

    async def get_placement(self, entry_id: uuid.UUID) -> PlantPlacement | None:
        result = await self.session.execute(
            select(PlantPlacement).where(PlantPlacement.entry_id == entry_id)
        )
        return result.scalar_one_or_none()

    async def get_latest_source(
        self, entry_id: uuid.UUID
    ) -> PlantKnowledgeSource | None:
        result = await self.session.execute(
            select(PlantKnowledgeSource)
            .where(PlantKnowledgeSource.entry_id == entry_id)
            .order_by(PlantKnowledgeSource.ingested_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
