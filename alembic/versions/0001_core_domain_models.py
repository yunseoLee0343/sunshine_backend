"""Core domain models baseline.

Revision ID: 0001
Revises:
Create Date: 2026-05-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------ users
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # -------------------------------------------------------- species_profiles
    op.create_table(
        "species_profiles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("korean_name", sa.Text(), nullable=False),
        sa.Column("scientific_name", sa.Text(), nullable=True),
        sa.Column("common_name", sa.Text(), nullable=True),
        sa.Column("care_level", sa.Text(), nullable=True),
        sa.Column("water_min_pct", sa.Numeric(), nullable=True),
        sa.Column("water_max_pct", sa.Numeric(), nullable=True),
        sa.Column("light_min_lux", sa.Numeric(), nullable=True),
        sa.Column("light_max_lux", sa.Numeric(), nullable=True),
        sa.Column("humidity_min_pct", sa.Numeric(), nullable=True),
        sa.Column("humidity_max_pct", sa.Numeric(), nullable=True),
        sa.Column("temperature_min_c", sa.Numeric(), nullable=True),
        sa.Column("temperature_max_c", sa.Numeric(), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # -------------------------------------------------------------- plants
    op.create_table(
        "plants",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("species_profile_id", sa.UUID(), nullable=True),
        sa.Column("nickname", sa.Text(), nullable=False),
        sa.Column("room_name", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["species_profile_id"], ["species_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # -------------------------------------------------------- plant_characters
    op.create_table(
        "plant_characters",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("plant_id", sa.UUID(), nullable=False),
        sa.Column("mood", sa.Text(), nullable=False),
        sa.Column("expression", sa.Text(), nullable=False),
        sa.Column("status_message", sa.Text(), nullable=False),
        sa.Column("reason_code", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # -------------------------------------------------------- sensor_readings
    op.create_table(
        "sensor_readings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("reading_id", sa.Text(), nullable=False),
        sa.Column("device_id", sa.Text(), nullable=False),
        sa.Column("plant_id", sa.UUID(), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("temperature_c", sa.Numeric(), nullable=False),
        sa.Column("humidity_pct", sa.Numeric(), nullable=False),
        sa.Column("light_lux", sa.Numeric(), nullable=False),
        sa.Column("soil_moisture_pct", sa.Numeric(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reading_id"),
    )

    # -------------------------------------------------- environment_snapshots
    op.create_table(
        "environment_snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("plant_id", sa.UUID(), nullable=False),
        sa.Column("window", sa.Text(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("temperature_avg_c", sa.Numeric(), nullable=True),
        sa.Column("temperature_min_c", sa.Numeric(), nullable=True),
        sa.Column("temperature_max_c", sa.Numeric(), nullable=True),
        sa.Column("humidity_avg_pct", sa.Numeric(), nullable=True),
        sa.Column("humidity_min_pct", sa.Numeric(), nullable=True),
        sa.Column("humidity_max_pct", sa.Numeric(), nullable=True),
        sa.Column("light_avg_lux", sa.Numeric(), nullable=True),
        sa.Column("light_min_lux", sa.Numeric(), nullable=True),
        sa.Column("light_max_lux", sa.Numeric(), nullable=True),
        sa.Column("soil_moisture_avg_pct", sa.Numeric(), nullable=True),
        sa.Column("soil_moisture_min_pct", sa.Numeric(), nullable=True),
        sa.Column("soil_moisture_max_pct", sa.Numeric(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plant_id", "window", "window_start", "window_end"),
    )

    # ------------------------------------------------------------- care_logs
    op.create_table(
        "care_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("plant_id", sa.UUID(), nullable=False),
        sa.Column("action_type", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("acted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ---------------------------------------------------------- chat_requests
    op.create_table(
        "chat_requests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("plant_id", sa.UUID(), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # --------------------------------------------------------------- llm_runs
    op.create_table(
        "llm_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("request_id", sa.UUID(), nullable=False),
        sa.Column("profile", sa.Text(), nullable=True),
        sa.Column("model_name", sa.Text(), nullable=True),
        sa.Column("prompt_hash", sa.Text(), nullable=True),
        sa.Column("prompt_text", sa.Text(), nullable=True),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["chat_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------ recommendation_evidence
    op.create_table(
        "recommendation_evidence",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("request_id", sa.UUID(), nullable=False),
        sa.Column("evidence_type", sa.Text(), nullable=False),
        sa.Column(
            "evidence_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["chat_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # -------------------------------------------------------- retrieved_chunks
    op.create_table(
        "retrieved_chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("request_id", sa.UUID(), nullable=False),
        sa.Column("chunk_id", sa.Text(), nullable=False),
        sa.Column("score", sa.Numeric(), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["chat_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("retrieved_chunks")
    op.drop_table("recommendation_evidence")
    op.drop_table("llm_runs")
    op.drop_table("chat_requests")
    op.drop_table("care_logs")
    op.drop_table("environment_snapshots")
    op.drop_table("sensor_readings")
    op.drop_table("plant_characters")
    op.drop_table("plants")
    op.drop_table("species_profiles")
    op.drop_table("users")
