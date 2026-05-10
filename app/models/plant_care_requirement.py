"""plant_care_requirements — TICKET-014A."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlantCareRequirement(Base):
    __tablename__ = "plant_care_requirements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("plant_knowledge_entries.id", ondelete="CASCADE"), nullable=False
    )
    growth_temp_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    light_requirement: Mapped[str | None] = mapped_column(Text, nullable=True)
    watering_frequency: Mapped[str | None] = mapped_column(Text, nullable=True)
    soil_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    fertilizer_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
