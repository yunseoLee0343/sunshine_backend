"""plant_knowledge_sources — TICKET-014A.

Tracks provenance, row hash, and ingest status for idempotency.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlantKnowledgeSource(Base):
    __tablename__ = "plant_knowledge_sources"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("plant_knowledge_entries.id", ondelete="CASCADE"), nullable=False
    )
    source_file: Mapped[str] = mapped_column(Text, nullable=False)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    nongsaro_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_row_hash: Mapped[str] = mapped_column(Text, nullable=False)
    ingest_status: Mapped[str] = mapped_column(Text, nullable=False)  # inserted/updated/ignored
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
