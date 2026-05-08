import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SpeciesProfile(Base):
    __tablename__ = "species_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    korean_name: Mapped[str] = mapped_column(Text, nullable=False)
    scientific_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    common_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    care_level: Mapped[str | None] = mapped_column(Text, nullable=True)
    water_min_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    water_max_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    light_min_lux: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    light_max_lux: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    humidity_min_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    humidity_max_pct: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    temperature_min_c: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    temperature_max_c: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
