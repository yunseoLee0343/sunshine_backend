"""TICKET-031: add audio fields to chat_requests.

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("chat_requests", sa.Column("audio_uri_in", sa.Text(), nullable=True))
    op.add_column("chat_requests", sa.Column("audio_uri_out", sa.Text(), nullable=True))
    op.add_column(
        "chat_requests",
        sa.Column("audio_duration_seconds", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat_requests", "audio_duration_seconds")
    op.drop_column("chat_requests", "audio_uri_out")
    op.drop_column("chat_requests", "audio_uri_in")
