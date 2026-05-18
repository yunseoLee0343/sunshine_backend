"""SensorMetricRollup — TICKET-068."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SensorMetricRollup(Base):
    __tablename__ = "sensor_metric_rollups"
    __table_args__ = (
        UniqueConstraint(
            "plant_id", "metric_name", "bucket", "bucket_start", "bucket_end",
            name="uq_sensor_metric_rollups_key",
        ),
        Index("ix_sensor_metric_rollups_plant_metric_bucket", "plant_id", "metric_name", "bucket"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    plant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("plants.id", ondelete="CASCADE"), nullable=False
    )
    metric_name: Mapped[str] = mapped_column(Text, nullable=False)
    bucket: Mapped[str] = mapped_column(Text, nullable=False)  # hourly | daily
    bucket_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    bucket_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    avg_value: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    min_value: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    max_value: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
