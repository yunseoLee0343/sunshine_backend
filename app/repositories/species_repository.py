"""SpeciesRepository — catalog lookup only.

No image classification, no model inference, no diagnosis fields.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.species_profile import SpeciesProfile

# Source identifier for Excel-imported catalog rows (TICKET-060A0)
CATALOG_SOURCE = "전체식물_분류정보_v1_updated_7_2.xlsx"


def _catalog_where():
    """Return SQLAlchemy WHERE clauses that restrict to Excel-catalog rows only."""
    return [
        SpeciesProfile.metadata_json["catalog_allowed"].astext == "true",
        SpeciesProfile.metadata_json["source"].astext == CATALOG_SOURCE,
    ]


class SpeciesRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_candidates(self, limit: int = 20) -> list[SpeciesProfile]:
        """Return first N species_profiles from the DB (catalog order)."""
        result = await self.session.execute(select(SpeciesProfile).limit(limit))
        return list(result.scalars().all())

    async def get_by_id(self, species_id: uuid.UUID) -> SpeciesProfile | None:
        result = await self.session.execute(select(SpeciesProfile).where(SpeciesProfile.id == species_id))
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Unrestricted lookups (kept for other callers / legacy compatibility)
    # ------------------------------------------------------------------

    async def find_by_scientific_name(self, scientific_name: str) -> SpeciesProfile | None:
        result = await self.session.execute(
            select(SpeciesProfile).where(SpeciesProfile.scientific_name == scientific_name)
        )
        return result.scalars().first()

    async def find_by_korean_name(self, korean_name: str) -> SpeciesProfile | None:
        result = await self.session.execute(select(SpeciesProfile).where(SpeciesProfile.korean_name == korean_name))
        return result.scalars().first()

    async def find_by_common_name(self, common_name: str) -> SpeciesProfile | None:
        result = await self.session.execute(select(SpeciesProfile).where(SpeciesProfile.common_name == common_name))
        return result.scalars().first()

    async def find_by_scientific_name_normalized(self, normalized: str) -> SpeciesProfile | None:
        result = await self.session.execute(
            select(SpeciesProfile).where(
                func.lower(
                    func.regexp_replace(SpeciesProfile.scientific_name, r"\s+", " ", "g")
                ) == normalized
            )
        )
        return result.scalars().first()

    async def find_by_common_name_normalized(self, normalized: str) -> SpeciesProfile | None:
        result = await self.session.execute(
            select(SpeciesProfile).where(
                func.lower(SpeciesProfile.common_name) == normalized
            )
        )
        return result.scalars().first()

    async def find_by_alias(self, normalized_alias: str) -> SpeciesProfile | None:
        alias_elem = func.jsonb_array_elements_text(
            SpeciesProfile.metadata_json["aliases"]
        ).column_valued("alias_elem", joins_implicitly=True)
        result = await self.session.execute(
            select(SpeciesProfile).where(
                func.lower(
                    func.regexp_replace(alias_elem, r"\s+", " ", "g")
                ) == normalized_alias
            )
        )
        return result.scalars().first()

    # ------------------------------------------------------------------
    # Catalog-constrained lookups — TICKET-060A2
    # Only rows where catalog_allowed=true AND source=CATALOG_SOURCE.
    # ------------------------------------------------------------------

    async def find_catalog_by_scientific_name(self, scientific_name: str) -> SpeciesProfile | None:
        result = await self.session.execute(
            select(SpeciesProfile).where(
                SpeciesProfile.scientific_name == scientific_name,
                *_catalog_where(),
            )
        )
        return result.scalars().first()

    async def find_catalog_by_korean_name(self, korean_name: str) -> SpeciesProfile | None:
        result = await self.session.execute(
            select(SpeciesProfile).where(
                SpeciesProfile.korean_name == korean_name,
                *_catalog_where(),
            )
        )
        return result.scalars().first()

    async def find_catalog_by_common_name(self, common_name: str) -> SpeciesProfile | None:
        result = await self.session.execute(
            select(SpeciesProfile).where(
                SpeciesProfile.common_name == common_name,
                *_catalog_where(),
            )
        )
        return result.scalars().first()

    async def find_catalog_by_scientific_name_normalized(self, normalized: str) -> SpeciesProfile | None:
        result = await self.session.execute(
            select(SpeciesProfile).where(
                func.lower(
                    func.regexp_replace(SpeciesProfile.scientific_name, r"\s+", " ", "g")
                ) == normalized,
                *_catalog_where(),
            )
        )
        return result.scalars().first()

    async def find_catalog_by_common_name_normalized(self, normalized: str) -> SpeciesProfile | None:
        result = await self.session.execute(
            select(SpeciesProfile).where(
                func.lower(SpeciesProfile.common_name) == normalized,
                *_catalog_where(),
            )
        )
        return result.scalars().first()

    async def find_catalog_by_alias(self, normalized_alias: str) -> SpeciesProfile | None:
        alias_elem = func.jsonb_array_elements_text(
            SpeciesProfile.metadata_json["aliases"]
        ).column_valued("alias_elem", joins_implicitly=True)
        result = await self.session.execute(
            select(SpeciesProfile).where(
                func.lower(
                    func.regexp_replace(alias_elem, r"\s+", " ", "g")
                ) == normalized_alias,
                *_catalog_where(),
            )
        )
        return result.scalars().first()
