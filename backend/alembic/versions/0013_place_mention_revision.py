"""Add optimistic concurrency to place mentions.

Revision ID: 0013
Revises: 0012
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("place_mentions")}
    if "revision" not in columns:
        op.add_column(
            "place_mentions", sa.Column("revision", sa.Integer(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    op.drop_column("place_mentions", "revision")
