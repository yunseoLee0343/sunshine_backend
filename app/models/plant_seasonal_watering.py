"""plant_seasonal_watering — TICKET-014A."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlantSeasonalWatering(Base):
    __tablename__ = "plant_seasonal_watering"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("plant_knowledge_entries.id", ondelete="CASCADE"), nullable=False
    )
    spring: Mapped[str | None] = mapped_column(Text, nullable=True)
    summer: Mapped[str | None] = mapped_column(Text, nullable=True)
    autumn: Mapped[str | None] = mapped_column(Text, nullable=True)
    winter: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
