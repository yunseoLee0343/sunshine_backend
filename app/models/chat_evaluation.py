"""Evaluation DB models — TICKET-034."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GroundTruthEntry(Base):
    __tablename__ = "ground_truth_entries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    question_keywords: Mapped[list] = mapped_column(JSONB, nullable=False)
    expected_answer: Mapped[str] = mapped_column(Text, nullable=False)
    required_keywords: Mapped[list] = mapped_column(JSONB, nullable=False)
    intent: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChatEvaluationResult(Base):
    __tablename__ = "chat_evaluation_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_requests.id"), nullable=False
    )
    ab_test_group: Mapped[str] = mapped_column(Text, nullable=False)
    faithfulness: Mapped[float] = mapped_column(Float, nullable=False)
    answer_relevance: Mapped[float] = mapped_column(Float, nullable=False)
    ground_truth_similarity: Mapped[float] = mapped_column(Float, nullable=False)
    matched_ground_truth_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
