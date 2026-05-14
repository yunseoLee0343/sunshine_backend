"""TICKET-048: add embedding_model_rev, query_vector_hash, chunk_builder_version, plant_id to retrieval_runs.

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "retrieval_runs",
        sa.Column("plant_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "retrieval_runs",
        sa.Column("embedding_model_rev", sa.Text(), nullable=True),
    )
    op.add_column(
        "retrieval_runs",
        sa.Column("query_vector_hash", sa.Text(), nullable=True),
    )
    op.add_column(
        "retrieval_runs",
        sa.Column("chunk_builder_version", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("retrieval_runs", "chunk_builder_version")
    op.drop_column("retrieval_runs", "query_vector_hash")
    op.drop_column("retrieval_runs", "embedding_model_rev")
    op.drop_column("retrieval_runs", "plant_id")
