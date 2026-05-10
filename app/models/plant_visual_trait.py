"""plant_visual_traits — TICKET-014A."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlantVisualTrait(Base):
    __tablename__ = "plant_visual_traits"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("plant_knowledge_entries.id", ondelete="CASCADE"), nullable=False
    )
    leaf_color: Mapped[str | None] = mapped_column(Text, nullable=True)
    leaf_shape: Mapped[str | None] = mapped_column(Text, nullable=True)
    flower_color: Mapped[str | None] = mapped_column(Text, nullable=True)
    flower_season: Mapped[str | None] = mapped_column(Text, nullable=True)
    height_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
