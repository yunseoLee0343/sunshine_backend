"""TICKET-014A: create plant knowledge relational tables.

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-10

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------ plant_knowledge_entries
    op.create_table(
        "plant_knowledge_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("nongsaro_id", sa.Text(), nullable=False),
        sa.Column("korean_name", sa.Text(), nullable=False),
        sa.Column("scientific_name", sa.Text(), nullable=True),
        sa.Column("common_name", sa.Text(), nullable=True),
        sa.Column("family", sa.Text(), nullable=True),
        sa.Column("origin", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nongsaro_id", name="uq_plant_knowledge_nongsaro_id"),
    )
    op.create_index(
        "ix_plant_knowledge_scientific_name",
        "plant_knowledge_entries",
        ["scientific_name"],
    )

    # -------------------------------------------- plant_care_requirements
    op.create_table(
        "plant_care_requirements",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("entry_id", sa.UUID(), nullable=False),
        sa.Column("growth_temp_text", sa.Text(), nullable=True),
        sa.Column("light_requirement", sa.Text(), nullable=True),
        sa.Column("watering_frequency", sa.Text(), nullable=True),
        sa.Column("soil_type", sa.Text(), nullable=True),
        sa.Column("fertilizer_info", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["entry_id"], ["plant_knowledge_entries.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # -------------------------------------------- plant_seasonal_watering
    op.create_table(
        "plant_seasonal_watering",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("entry_id", sa.UUID(), nullable=False),
        sa.Column("spring", sa.Text(), nullable=True),
        sa.Column("summer", sa.Text(), nullable=True),
        sa.Column("autumn", sa.Text(), nullable=True),
        sa.Column("winter", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["entry_id"], ["plant_knowledge_entries.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ----------------------------------------------- plant_pest_references
    op.create_table(
        "plant_pest_references",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("entry_id", sa.UUID(), nullable=False),
        sa.Column("pest_text", sa.Text(), nullable=True),
        sa.Column("disease_text", sa.Text(), nullable=True),
        sa.Column(
            "parsed_pest_terms",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["entry_id"], ["plant_knowledge_entries.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------- plant_visual_traits
    op.create_table(
        "plant_visual_traits",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("entry_id", sa.UUID(), nullable=False),
        sa.Column("leaf_color", sa.Text(), nullable=True),
        sa.Column("leaf_shape", sa.Text(), nullable=True),
        sa.Column("flower_color", sa.Text(), nullable=True),
        sa.Column("flower_season", sa.Text(), nullable=True),
        sa.Column("height_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["entry_id"], ["plant_knowledge_entries.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ---------------------------------------------------- plant_placements
    op.create_table(
        "plant_placements",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("entry_id", sa.UUID(), nullable=False),
        sa.Column("placement_locations", sa.Text(), nullable=True),
        sa.Column("is_toxic", sa.Boolean(), nullable=True),
        sa.Column("toxicity_detail", sa.Text(), nullable=True),
        sa.Column("fragrance", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["entry_id"], ["plant_knowledge_entries.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ----------------------------------------- plant_knowledge_sources
    op.create_table(
        "plant_knowledge_sources",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("entry_id", sa.UUID(), nullable=False),
        sa.Column("source_file", sa.Text(), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("nongsaro_id", sa.Text(), nullable=True),
        sa.Column("source_row_hash", sa.Text(), nullable=False),
        sa.Column("ingest_status", sa.Text(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["entry_id"], ["plant_knowledge_entries.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_plant_knowledge_sources_entry_id",
        "plant_knowledge_sources",
        ["entry_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_plant_knowledge_sources_entry_id", "plant_knowledge_sources")
    op.drop_table("plant_knowledge_sources")
    op.drop_table("plant_placements")
    op.drop_table("plant_visual_traits")
    op.drop_table("plant_pest_references")
    op.drop_table("plant_seasonal_watering")
    op.drop_table("plant_care_requirements")
    op.drop_index("ix_plant_knowledge_scientific_name", "plant_knowledge_entries")
    op.drop_table("plant_knowledge_entries")
