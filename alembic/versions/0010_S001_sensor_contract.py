"""S-001: align MQTT sensor contract — nullable metrics, external_plant_id, device_id.

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Make sensor_readings metric columns nullable (sensor MVP sends null on failure)
    op.alter_column("sensor_readings", "temperature_c", nullable=True)
    op.alter_column("sensor_readings", "humidity_pct", nullable=True)
    op.alter_column("sensor_readings", "light_lux", nullable=True)
    op.alter_column("sensor_readings", "soil_moisture_pct", nullable=True)

    # Add external plant identifier and device binding columns to plants
    op.add_column("plants", sa.Column("external_plant_id", sa.Text(), nullable=True))
    op.add_column("plants", sa.Column("device_id", sa.Text(), nullable=True))

    op.create_unique_constraint("uq_plants_external_plant_id", "plants", ["external_plant_id"])
    op.create_index("ix_plants_device_id", "plants", ["device_id"])


def downgrade() -> None:
    op.drop_index("ix_plants_device_id", table_name="plants")
    op.drop_constraint("uq_plants_external_plant_id", "plants", type_="unique")
    op.drop_column("plants", "device_id")
    op.drop_column("plants", "external_plant_id")

    op.alter_column("sensor_readings", "soil_moisture_pct", nullable=False)
    op.alter_column("sensor_readings", "light_lux", nullable=False)
    op.alter_column("sensor_readings", "humidity_pct", nullable=False)
    op.alter_column("sensor_readings", "temperature_c", nullable=False)
