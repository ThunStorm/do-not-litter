"""Persist the render profile that produced each immutable Note version.

Revision ID: 0021
Revises: 0020
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("ai_note_versions")}
    if "render_profile_id" not in columns:
        op.add_column(
            "ai_note_versions",
            sa.Column("render_profile_id", sa.String(64), nullable=False, server_default="CURRENT_DEFAULT"),
        )
    if "render_profile_version" not in columns:
        op.add_column(
            "ai_note_versions",
            sa.Column("render_profile_version", sa.String(32), nullable=False, server_default="1"),
        )


def downgrade() -> None:
    op.drop_column("ai_note_versions", "render_profile_version")
    op.drop_column("ai_note_versions", "render_profile_id")
