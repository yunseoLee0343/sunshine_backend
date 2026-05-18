import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlantSensorDevice(Base):
    __tablename__ = "plant_sensor_devices"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    plant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("plants.id", ondelete="CASCADE"), nullable=False
    )
    device_id: Mapped[str] = mapped_column(Text, nullable=False)
    device_role: Mapped[str] = mapped_column(Text, nullable=False)  # soil | leaf_env | unknown
    location_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("plant_id", "device_id", name="uq_plant_sensor_devices_plant_device"),
        Index("ix_plant_sensor_devices_device_id", "device_id"),
        Index("ix_plant_sensor_devices_plant_id", "plant_id"),
    )
