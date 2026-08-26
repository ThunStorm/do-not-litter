"""Add v0.4 screenshots, marker lifecycle and granular place fields.

Revision ID: 0004
Revises: 0003
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "video_screenshots" in sa.inspect(op.get_bind()).get_table_names():
        return
    with op.batch_alter_table("places") as batch:
        batch.add_column(sa.Column("canonical_name", sa.String(300), nullable=False, server_default=""))
        batch.add_column(sa.Column("origin", sa.String(32), nullable=False, server_default="AI_EXTRACTED"))
    with op.batch_alter_table("place_mentions") as batch:
        batch.add_column(sa.Column("raw_name", sa.String(300), nullable=False, server_default=""))
        batch.add_column(sa.Column("suggested_name", sa.String(300), nullable=False, server_default=""))
        batch.add_column(sa.Column("brief_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.create_table(
        "map_marker_states",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("place_id", sa.String(64), sa.ForeignKey("places.id", ondelete="CASCADE"), nullable=False),
        sa.Column("origin", sa.String(32), nullable=False),
        sa.Column("visibility", sa.String(32), nullable=False),
        sa.Column("custom_label", sa.String(300)),
        sa.Column("created_by", sa.String(64), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("place_id", name="uq_map_marker_place"),
    )
    op.create_table(
        "video_screenshots",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("video_asset_id", sa.String(64), sa.ForeignKey("video_assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ai_note_version_id", sa.String(64), sa.ForeignKey("ai_note_versions.id", ondelete="SET NULL")),
        sa.Column("ai_note_section_id", sa.String(64), sa.ForeignKey("ai_note_sections.id", ondelete="SET NULL")),
        sa.Column("place_mention_id", sa.String(64), sa.ForeignKey("place_mentions.id", ondelete="SET NULL")),
        sa.Column("segment_id", sa.String(64), sa.ForeignKey("segments.id", ondelete="SET NULL")),
        sa.Column("planned_timestamp_ms", sa.Integer(), nullable=False),
        sa.Column("actual_timestamp_ms", sa.Integer()),
        sa.Column("image_path", sa.Text()),
        sa.Column("content_hash", sa.String(128)),
        sa.Column("perceptual_hash", sa.String(128)),
        sa.Column("width", sa.Integer()),
        sa.Column("height", sa.Integer()),
        sa.Column("quality_score", sa.Float()),
        sa.Column("selection_reason", sa.String(500), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_video_screenshots_asset", "video_screenshots", ["video_asset_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_video_screenshots_asset", table_name="video_screenshots")
    op.drop_table("video_screenshots")
    op.drop_table("map_marker_states")
    with op.batch_alter_table("place_mentions") as batch:
        batch.drop_column("brief_json")
        batch.drop_column("suggested_name")
        batch.drop_column("raw_name")
    with op.batch_alter_table("places") as batch:
        batch.drop_column("origin")
        batch.drop_column("canonical_name")
