"""Add exact AI execution cache entries.

Revision ID: 0010
Revises: 0009
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "ai_cache_entries" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "ai_cache_entries",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("cache_key", sa.String(128), nullable=False),
        sa.Column("stage", sa.String(64), nullable=False),
        sa.Column("capability", sa.String(64), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("model", sa.String(160), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("previous_entry_id", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ai_cache_key_created", "ai_cache_entries", ["cache_key", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_ai_cache_key_created", table_name="ai_cache_entries")
    op.drop_table("ai_cache_entries")
