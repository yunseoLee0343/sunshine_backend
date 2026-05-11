"""TICKET-034: create ground_truth_entries and chat_evaluation_results tables.

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ground_truth_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "question_keywords",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("expected_answer", sa.Text(), nullable=False),
        sa.Column(
            "required_keywords",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("intent", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ground_truth_entries_intent",
        "ground_truth_entries",
        ["intent"],
    )

    op.create_table(
        "chat_evaluation_results",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("request_id", sa.UUID(), nullable=False),
        sa.Column("ab_test_group", sa.Text(), nullable=False),
        sa.Column("faithfulness", sa.Float(), nullable=False),
        sa.Column("answer_relevance", sa.Float(), nullable=False),
        sa.Column("ground_truth_similarity", sa.Float(), nullable=False),
        sa.Column("matched_ground_truth_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["chat_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_chat_evaluation_results_request_id",
        "chat_evaluation_results",
        ["request_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_chat_evaluation_results_request_id", "chat_evaluation_results")
    op.drop_table("chat_evaluation_results")
    op.drop_index("ix_ground_truth_entries_intent", "ground_truth_entries")
    op.drop_table("ground_truth_entries")
