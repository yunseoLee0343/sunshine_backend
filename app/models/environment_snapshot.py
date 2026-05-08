import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EnvironmentSnapshot(Base):
    __tablename__ = "environment_snapshots"
    __table_args__ = (UniqueConstraint("plant_id", "window", "window_start", "window_end"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    plant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plants.id"), nullable=False)
    window: Mapped[str] = mapped_column(Text, nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    temperature_avg_c: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    temperature_min_c: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    temperature_max_c: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    humidity_avg_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    humidity_min_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    humidity_max_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    light_avg_lux: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    light_min_lux: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    light_max_lux: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    soil_moisture_avg_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    soil_moisture_min_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    soil_moisture_max_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
