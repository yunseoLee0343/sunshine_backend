"""TICKET-068: create sensor_metric_rollups table for 7-day rollup retention.

Revision ID: 0016
Revises: 0015
Create Date: 2026-05-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sensor_metric_rollups",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("plant_id", sa.UUID(), nullable=False),
        sa.Column("metric_name", sa.Text(), nullable=False),
        sa.Column("bucket", sa.Text(), nullable=False),
        sa.Column("bucket_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bucket_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("avg_value", sa.Numeric(), nullable=True),
        sa.Column("min_value", sa.Numeric(), nullable=True),
        sa.Column("max_value", sa.Numeric(), nullable=True),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "plant_id", "metric_name", "bucket", "bucket_start", "bucket_end",
            name="uq_sensor_metric_rollups_key",
        ),
    )
    op.create_index(
        "ix_sensor_metric_rollups_plant_metric_bucket",
        "sensor_metric_rollups",
        ["plant_id", "metric_name", "bucket"],
    )


def downgrade() -> None:
    op.drop_index("ix_sensor_metric_rollups_plant_metric_bucket", "sensor_metric_rollups")
    op.drop_table("sensor_metric_rollups")
