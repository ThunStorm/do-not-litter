"""add travel preference events and visual facts

Revision ID: 0019
Revises: 0018
"""

import sqlalchemy as sa

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "preference_events",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("place_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=16), nullable=False),
        sa.Column("actor", sa.String(length=32), nullable=False, server_default="user"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["place_id"], ["places.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_preference_events_place_created", "preference_events", ["place_id", "created_at"])
    op.create_table(
        "visual_facts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("screenshot_id", sa.String(length=64), nullable=False),
        sa.Column("place_id", sa.String(length=64), nullable=True),
        sa.Column("source_id", sa.String(length=64), nullable=True),
        sa.Column("fact_type", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("timestamp_ms", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("model", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("model_version", sa.String(length=64), nullable=False, server_default="vision-fact-v1"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="EXPERIMENTAL"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["screenshot_id"], ["video_screenshots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["place_id"], ["places.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_visual_facts_screenshot_status", "visual_facts", ["screenshot_id", "status"])
    op.create_index("ix_visual_facts_place_status", "visual_facts", ["place_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_visual_facts_place_status", table_name="visual_facts")
    op.drop_index("ix_visual_facts_screenshot_status", table_name="visual_facts")
    op.drop_table("visual_facts")
    op.drop_index("ix_preference_events_place_created", table_name="preference_events")
    op.drop_table("preference_events")
