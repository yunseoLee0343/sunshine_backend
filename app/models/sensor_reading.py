import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reading_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    device_id: Mapped[str] = mapped_column(Text, nullable=False)
    plant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plants.id"), nullable=False)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    temperature_c: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    humidity_pct: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    light_lux: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    soil_moisture_pct: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
