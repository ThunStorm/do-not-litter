"""Add transcript correction fields and local video covers.

Revision ID: 0006
Revises: 0005
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "video_cover_assets" in sa.inspect(op.get_bind()).get_table_names():
        return
    with op.batch_alter_table("segments") as batch:
        batch.add_column(sa.Column("raw_text", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("corrected_text", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("correction_status", sa.String(32), nullable=False, server_default="UNCORRECTED"))
        batch.add_column(sa.Column("correction_confidence", sa.Float()))
        batch.add_column(sa.Column("correction_reason", sa.String(500), nullable=False, server_default=""))
        batch.add_column(sa.Column("correction_provider", sa.String(64), nullable=False, server_default=""))
        batch.add_column(sa.Column("correction_model", sa.String(160), nullable=False, server_default=""))
    op.execute("UPDATE segments SET raw_text = text, corrected_text = text WHERE kind = 'VIDEO_TRANSCRIPT'")
    op.create_table(
        "video_cover_assets",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("video_asset_id", sa.String(64), sa.ForeignKey("video_assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False), sa.Column("local_path", sa.Text()), sa.Column("derivative_path", sa.Text()),
        sa.Column("content_hash", sa.String(128)), sa.Column("content_type", sa.String(80), nullable=False),
        sa.Column("width", sa.Integer()), sa.Column("height", sa.Integer()), sa.Column("byte_size", sa.Integer()),
        sa.Column("status", sa.String(32), nullable=False), sa.Column("error_code", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("video_asset_id", name="uq_cover_asset_video"),
    )


def downgrade() -> None:
    op.drop_table("video_cover_assets")
    with op.batch_alter_table("segments") as batch:
        for name in ("correction_model", "correction_provider", "correction_reason", "correction_confidence", "correction_status", "corrected_text", "raw_text"):
            batch.drop_column(name)
