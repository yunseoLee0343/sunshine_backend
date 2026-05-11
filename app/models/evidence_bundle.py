"""evidence_bundles — TICKET-015."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EvidenceBundle(Base):
    __tablename__ = "evidence_bundles"
    __table_args__ = (UniqueConstraint("evidence_hash", name="uq_evidence_bundle_hash"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    evidence_hash: Mapped[str] = mapped_column(Text, nullable=False)
    plant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str] = mapped_column(Text, nullable=False)
    rag_layers: Mapped[list] = mapped_column(JSONB, nullable=False)
    source_coverage: Mapped[dict] = mapped_column(JSONB, nullable=False)
    bundle_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
