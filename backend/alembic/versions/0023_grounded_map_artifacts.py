"""Persist profile-independent grounded maps for video-note reuse.

Revision ID: 0023
Revises: 0022
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "grounded_map_artifacts" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "grounded_map_artifacts",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "video_asset_id",
            sa.String(64),
            sa.ForeignKey("video_assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "transcript_id",
            sa.String(64),
            sa.ForeignKey("transcripts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("transcript_version", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(128), nullable=False),
        sa.Column("semantic_hash", sa.String(128), nullable=False),
        sa.Column("prompt_version", sa.String(64), nullable=False),
        sa.Column("supplement_hash", sa.String(128), nullable=False),
        sa.Column("domain", sa.String(80), nullable=False, server_default="travel"),
        sa.Column("domain_pack_version", sa.String(128), nullable=False, server_default=""),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("model", sa.String(160), nullable=False),
        sa.Column("semantic_options_json", sa.JSON(), nullable=False),
        sa.Column("facts_json", sa.JSON(), nullable=False),
        sa.Column("places_json", sa.JSON(), nullable=False),
        sa.Column("warnings_json", sa.JSON(), nullable=False),
        sa.Column("producer_version", sa.String(32), nullable=False, server_default="grounded-map-v1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("semantic_hash", name="uq_grounded_map_semantic_hash"),
    )
    op.create_index(
        "ix_grounded_map_transcript",
        "grounded_map_artifacts",
        ["transcript_id", "transcript_version"],
    )


def downgrade() -> None:
    op.drop_index("ix_grounded_map_transcript", table_name="grounded_map_artifacts")
    op.drop_table("grounded_map_artifacts")
