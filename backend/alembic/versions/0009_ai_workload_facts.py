"""Persist compact AI map facts for deterministic downstream aggregation.

Revision ID: 0009
Revises: 0008
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("ai_note_versions")}
    if "map_facts_json" in columns:
        return
    op.add_column(
        "ai_note_versions",
        sa.Column("map_facts_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )


def downgrade() -> None:
    op.drop_column("ai_note_versions", "map_facts_json")
