"""TICKET-066: add plant_sensor_devices for multi-device sensor authorization.

Revision ID: 0014
Revises: 0013
Create Date: 2026-05-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "plant_sensor_devices",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "plant_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("plants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("device_id", sa.Text, nullable=False),
        sa.Column("device_role", sa.Text, nullable=False),
        sa.Column("location_label", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_unique_constraint(
        "uq_plant_sensor_devices_plant_device",
        "plant_sensor_devices",
        ["plant_id", "device_id"],
    )
    op.create_index("ix_plant_sensor_devices_device_id", "plant_sensor_devices", ["device_id"])
    op.create_index("ix_plant_sensor_devices_plant_id", "plant_sensor_devices", ["plant_id"])


def downgrade() -> None:
    op.drop_index("ix_plant_sensor_devices_plant_id", table_name="plant_sensor_devices")
    op.drop_index("ix_plant_sensor_devices_device_id", table_name="plant_sensor_devices")
    op.drop_table("plant_sensor_devices")
