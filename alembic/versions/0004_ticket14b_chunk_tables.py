"""TICKET-014B: create plant chunk document and embedding tables.

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------- plant_chunk_documents
    op.create_table(
        "plant_chunk_documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("plant_knowledge_id", sa.UUID(), nullable=False),
        sa.Column("chunk_kind", sa.Text(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("text_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["plant_knowledge_id"],
            ["plant_knowledge_entries.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "plant_knowledge_id", "chunk_kind",
            name="uq_chunk_document_entry_kind",
        ),
    )
    op.create_index(
        "ix_plant_chunk_documents_plant_knowledge_id",
        "plant_chunk_documents",
        ["plant_knowledge_id"],
    )

    # ------------------------------------------- plant_chunk_embeddings
    op.create_table(
        "plant_chunk_embeddings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("chunk_document_id", sa.UUID(), nullable=False),
        sa.Column("model_name", sa.Text(), nullable=False),
        sa.Column("vector_dim", sa.Integer(), nullable=False),
        sa.Column(
            "vector",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["chunk_document_id"],
            ["plant_chunk_documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chunk_document_id", name="uq_chunk_embedding_document"),
    )


def downgrade() -> None:
    op.drop_table("plant_chunk_embeddings")
    op.drop_index(
        "ix_plant_chunk_documents_plant_knowledge_id", "plant_chunk_documents"
    )
    op.drop_table("plant_chunk_documents")
