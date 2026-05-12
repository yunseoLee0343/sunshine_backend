import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Plant(Base):
    __tablename__ = "plants"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    species_profile_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("species_profiles.id"), nullable=True)
    nickname: Mapped[str] = mapped_column(Text, nullable=False)
    room_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_plant_id: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)
    device_id: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
