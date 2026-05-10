"""TICKET-014C: create retrieval_runs and retrieval_result_chunks tables.

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # -------------------------------------------------- retrieval_runs
    op.create_table(
        "retrieval_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("question_hash", sa.Text(), nullable=False),
        sa.Column("species_profile_id", sa.UUID(), nullable=True),
        sa.Column(
            "rag_layers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("top_k", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.Text(), nullable=False),
        sa.Column("total_results", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_retrieval_runs_user_id", "retrieval_runs", ["user_id"]
    )

    # ------------------------------------------ retrieval_result_chunks
    op.create_table(
        "retrieval_result_chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("chunk_document_id", sa.UUID(), nullable=False),
        sa.Column("plant_knowledge_id", sa.UUID(), nullable=False),
        sa.Column("chunk_kind", sa.Text(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"], ["retrieval_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_retrieval_result_chunks_run_id",
        "retrieval_result_chunks",
        ["run_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_retrieval_result_chunks_run_id", "retrieval_result_chunks")
    op.drop_table("retrieval_result_chunks")
    op.drop_index("ix_retrieval_runs_user_id", "retrieval_runs")
    op.drop_table("retrieval_runs")
