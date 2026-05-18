"""TICKET-067: compact environment_snapshots to one row per (plant_id, window).

Replaces the 4-column unique constraint (plant_id, window, window_start, window_end)
with a 2-column unique constraint (plant_id, window) so repeated aggregation runs
upsert into the same row instead of creating new rows.

Revision ID: 0015
Revises: 0014
Create Date: 2026-05-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the auto-named unique constraint on (plant_id, window, window_start, window_end).
    # The constraint has no explicit name in the original migration, so we look it up
    # dynamically to avoid relying on the PostgreSQL-generated truncated identifier.
    op.execute(
        """
        DO $$
        DECLARE
            cname text;
        BEGIN
            SELECT conname INTO cname
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            WHERE t.relname = 'environment_snapshots'
              AND c.contype = 'u'
              AND pg_get_constraintdef(c.oid) LIKE '%window_start%';
            IF cname IS NOT NULL THEN
                EXECUTE 'ALTER TABLE environment_snapshots DROP CONSTRAINT ' || quote_ident(cname);
            END IF;
        END $$;
        """
    )

    op.create_unique_constraint(
        "uq_environment_snapshots_plant_window",
        "environment_snapshots",
        ["plant_id", "window"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_environment_snapshots_plant_window",
        "environment_snapshots",
        type_="unique",
    )

    op.create_unique_constraint(
        None,
        "environment_snapshots",
        ["plant_id", "window", "window_start", "window_end"],
    )
