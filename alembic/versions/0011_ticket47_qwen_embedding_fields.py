"""TICKET-047: add vector_norm and text_hash_at_embed to plant_chunk_embeddings.

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "plant_chunk_embeddings",
        sa.Column("vector_norm", sa.Float(), nullable=True),
    )
    op.add_column(
        "plant_chunk_embeddings",
        sa.Column("text_hash_at_embed", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("plant_chunk_embeddings", "text_hash_at_embed")
    op.drop_column("plant_chunk_embeddings", "vector_norm")
