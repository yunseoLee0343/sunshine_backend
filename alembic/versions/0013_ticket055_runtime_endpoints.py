"""TICKET-055: add runtime_endpoints table for dynamic vLLM endpoint registry.

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "runtime_endpoints",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text, nullable=False, unique=True),
        sa.Column("provider", sa.Text, nullable=False),
        sa.Column("model", sa.Text, nullable=False),
        sa.Column("base_url", sa.Text, nullable=False),
        sa.Column("api_key_secret_ref", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("health_status", sa.Text, nullable=True),
        sa.Column("last_health_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_runtime_endpoints_name", "runtime_endpoints", ["name"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_runtime_endpoints_name", table_name="runtime_endpoints")
    op.drop_table("runtime_endpoints")
