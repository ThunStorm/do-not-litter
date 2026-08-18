"""Add durable audit events.

Revision ID: 0002
Revises: 0001
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_events",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("component", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=True),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("detail_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_system_events_created", "system_events", ["created_at"])
    op.create_index("ix_system_events_component_level", "system_events", ["component", "level"])


def downgrade() -> None:
    op.drop_index("ix_system_events_component_level", table_name="system_events")
    op.drop_index("ix_system_events_created", table_name="system_events")
    op.drop_table("system_events")
