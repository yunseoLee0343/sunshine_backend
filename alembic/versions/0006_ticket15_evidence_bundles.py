"""TICKET-015: create evidence_bundles table.

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence_bundles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("evidence_hash", sa.Text(), nullable=False),
        sa.Column("plant_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("intent", sa.Text(), nullable=False),
        sa.Column(
            "rag_layers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "source_coverage",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "bundle_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evidence_hash", name="uq_evidence_bundle_hash"),
    )
    op.create_index(
        "ix_evidence_bundles_plant_id", "evidence_bundles", ["plant_id"]
    )
    op.create_index(
        "ix_evidence_bundles_evidence_hash", "evidence_bundles", ["evidence_hash"]
    )


def downgrade() -> None:
    op.drop_index("ix_evidence_bundles_evidence_hash", "evidence_bundles")
    op.drop_index("ix_evidence_bundles_plant_id", "evidence_bundles")
    op.drop_table("evidence_bundles")
