"""plant_chunk_embeddings — TICKET-047.

Stores the embedding vector as JSONB (list[float]) to avoid a pgvector
dependency on the application server. The vector dimension and model name
are recorded for future migration to a native vector type.

vector_norm and text_hash_at_embed added in TICKET-047 for quality checks.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlantChunkEmbedding(Base):
    __tablename__ = "plant_chunk_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    chunk_document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("plant_chunk_documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    model_name: Mapped[str] = mapped_column(Text, nullable=False)
    vector_dim: Mapped[int] = mapped_column(Integer, nullable=False)
    vector: Mapped[list] = mapped_column(JSONB, nullable=False)
    vector_norm: Mapped[float | None] = mapped_column(Float, nullable=True)
    text_hash_at_embed: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
