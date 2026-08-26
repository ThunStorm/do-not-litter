"""Add video transcript retention markers.

Revision ID: 0005
Revises: 0004
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("transcripts")}
    if "retention_until" in columns:
        return
    with op.batch_alter_table("transcripts") as batch:
        batch.add_column(sa.Column("retention_until", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("purged_at", sa.DateTime(timezone=True)))
    op.execute("UPDATE transcripts SET retention_until = datetime(created_at, '+180 days') WHERE retention_until IS NULL")


def downgrade() -> None:
    with op.batch_alter_table("transcripts") as batch:
        batch.drop_column("purged_at")
        batch.drop_column("retention_until")
