"""Bind each place insight to its own source evidence.

Revision ID: 0018
Revises: 0017
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("place_insight_items")}
    if "source_quote" not in columns:
        op.add_column(
            "place_insight_items",
            sa.Column("source_quote", sa.Text(), nullable=False, server_default=""),
        )


def downgrade() -> None:
    op.drop_column("place_insight_items", "source_quote")
