"""TICKET-004: add primary_action to plant_characters and latest-state index.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-10

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "plant_characters",
        sa.Column(
            "primary_action",
            sa.Text(),
            nullable=False,
            server_default="none",
        ),
    )
    op.create_index(
        "ix_plant_characters_plant_id_created_at",
        "plant_characters",
        ["plant_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_plant_characters_plant_id_created_at",
        table_name="plant_characters",
    )
    op.drop_column("plant_characters", "primary_action")
