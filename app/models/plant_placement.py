"""plant_placements — TICKET-014A."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlantPlacement(Base):
    __tablename__ = "plant_placements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("plant_knowledge_entries.id", ondelete="CASCADE"), nullable=False
    )
    placement_locations: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_toxic: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    toxicity_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    fragrance: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
