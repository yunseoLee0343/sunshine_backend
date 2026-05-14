"""retrieval_runs — TICKET-014C / TICKET-048."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RetrievalRun(Base):
    __tablename__ = "retrieval_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)  # == request_id
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    plant_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    question_hash: Mapped[str] = mapped_column(Text, nullable=False)
    species_profile_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    rag_layers: Mapped[list] = mapped_column(JSONB, nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False)
    model_name: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_model_rev: Mapped[str | None] = mapped_column(Text, nullable=True)
    query_vector_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_builder_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_results: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
