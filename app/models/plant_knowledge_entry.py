"""plant_knowledge_entries — TICKET-014A."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlantKnowledgeEntry(Base):
    __tablename__ = "plant_knowledge_entries"
    __table_args__ = (
        UniqueConstraint("nongsaro_id", name="uq_plant_knowledge_nongsaro_id"),
        Index("ix_plant_knowledge_scientific_name", "scientific_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nongsaro_id: Mapped[str] = mapped_column(Text, nullable=False)
    korean_name: Mapped[str] = mapped_column(Text, nullable=False)
    scientific_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    common_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    family: Mapped[str | None] = mapped_column(Text, nullable=True)
    origin: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
