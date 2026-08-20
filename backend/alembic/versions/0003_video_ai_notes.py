"""Add durable video AI note pipeline entities.

Revision ID: 0003
Revises: 0002
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("error_code", sa.String(length=64), nullable=True))
    op.add_column("job_steps", sa.Column("input_hash", sa.String(length=128), nullable=True))
    op.create_table("video_assets", sa.Column("id", sa.String(64), primary_key=True), sa.Column("source_id", sa.String(64), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("platform", sa.String(32), nullable=False), sa.Column("canonical_url", sa.Text(), nullable=False), sa.Column("bvid", sa.String(32)), sa.Column("aid", sa.String(32)), sa.Column("cid", sa.String(32)), sa.Column("page_number", sa.Integer(), nullable=False), sa.Column("title", sa.String(500), nullable=False), sa.Column("uploader", sa.String(200), nullable=False), sa.Column("duration_ms", sa.Integer()), sa.Column("cover_url", sa.Text()), sa.Column("metadata_json", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("canonical_url", name="uq_video_asset_canonical_url"))
    op.create_table("transcripts", sa.Column("id", sa.String(64), primary_key=True), sa.Column("video_asset_id", sa.String(64), sa.ForeignKey("video_assets.id", ondelete="CASCADE"), nullable=False), sa.Column("version", sa.Integer(), nullable=False), sa.Column("source_kind", sa.String(32), nullable=False), sa.Column("language", sa.String(24), nullable=False), sa.Column("text", sa.Text(), nullable=False), sa.Column("segment_count", sa.Integer(), nullable=False), sa.Column("metadata_json", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("video_asset_id", "version", name="uq_transcript_asset_version"))
    op.create_table("ai_notes", sa.Column("id", sa.String(64), primary_key=True), sa.Column("video_asset_id", sa.String(64), sa.ForeignKey("video_assets.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("current_version_id", sa.String(64)), sa.Column("status", sa.String(32), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("ai_note_versions", sa.Column("id", sa.String(64), primary_key=True), sa.Column("ai_note_id", sa.String(64), sa.ForeignKey("ai_notes.id", ondelete="CASCADE"), nullable=False), sa.Column("version", sa.Integer(), nullable=False), sa.Column("markdown", sa.Text(), nullable=False), sa.Column("overview", sa.Text(), nullable=False), sa.Column("warnings_json", sa.JSON(), nullable=False), sa.Column("model_provider", sa.String(64), nullable=False), sa.Column("model_name", sa.String(160), nullable=False), sa.Column("prompt_version", sa.String(32), nullable=False), sa.Column("transcript_version", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("ai_note_id", "version", name="uq_ai_note_version"))
    op.create_table("ai_note_sections", sa.Column("id", sa.String(64), primary_key=True), sa.Column("ai_note_version_id", sa.String(64), sa.ForeignKey("ai_note_versions.id", ondelete="CASCADE"), nullable=False), sa.Column("ordinal", sa.Integer(), nullable=False), sa.Column("heading", sa.String(500), nullable=False), sa.Column("body_markdown", sa.Text(), nullable=False), sa.Column("segment_ids_json", sa.JSON(), nullable=False), sa.Column("start_ms", sa.Integer()), sa.Column("end_ms", sa.Integer()), sa.UniqueConstraint("ai_note_version_id", "ordinal", name="uq_ai_note_section_order"))
    op.create_table("place_mentions", sa.Column("id", sa.String(64), primary_key=True), sa.Column("video_asset_id", sa.String(64), sa.ForeignKey("video_assets.id", ondelete="CASCADE"), nullable=False), sa.Column("ai_note_version_id", sa.String(64), sa.ForeignKey("ai_note_versions.id", ondelete="SET NULL")), sa.Column("name", sa.String(300), nullable=False), sa.Column("city_hint", sa.String(64), nullable=False), sa.Column("province_hint", sa.String(64), nullable=False), sa.Column("place_type", sa.String(64), nullable=False), sa.Column("reason", sa.Text(), nullable=False), sa.Column("quote", sa.Text(), nullable=False), sa.Column("segment_ids_json", sa.JSON(), nullable=False), sa.Column("confidence", sa.Float(), nullable=False), sa.Column("extraction_status", sa.String(32), nullable=False), sa.Column("resolution_status", sa.String(32), nullable=False), sa.Column("place_id", sa.String(64), sa.ForeignKey("places.id", ondelete="SET NULL")), sa.Column("metadata_json", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_place_mentions_asset_status", "place_mentions", ["video_asset_id", "resolution_status"])
    op.create_table("place_note_versions", sa.Column("id", sa.String(64), primary_key=True), sa.Column("place_id", sa.String(64), sa.ForeignKey("places.id", ondelete="CASCADE"), nullable=False), sa.Column("version", sa.Integer(), nullable=False), sa.Column("markdown", sa.Text(), nullable=False), sa.Column("model_provider", sa.String(64), nullable=False), sa.Column("model_name", sa.String(160), nullable=False), sa.Column("evidence_count", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("place_id", "version", name="uq_place_note_version"))
    op.create_table("external_call_audits", sa.Column("id", sa.String(64), primary_key=True), sa.Column("job_id", sa.String(64), sa.ForeignKey("jobs.id", ondelete="SET NULL")), sa.Column("capability", sa.String(64), nullable=False), sa.Column("provider", sa.String(64), nullable=False), sa.Column("operation", sa.String(128), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("duration_ms", sa.Integer()), sa.Column("request_meta_json", sa.JSON(), nullable=False), sa.Column("response_meta_json", sa.JSON(), nullable=False), sa.Column("error_code", sa.String(64)), sa.Column("error_message", sa.String(500)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_external_call_audits_job_created", "external_call_audits", ["job_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_external_call_audits_job_created", table_name="external_call_audits")
    op.drop_table("external_call_audits")
    op.drop_table("place_note_versions")
    op.drop_index("ix_place_mentions_asset_status", table_name="place_mentions")
    op.drop_table("place_mentions")
    op.drop_table("ai_note_sections")
    op.drop_table("ai_note_versions")
    op.drop_table("ai_notes")
    op.drop_table("transcripts")
    op.drop_table("video_assets")
    op.drop_column("job_steps", "input_hash")
    op.drop_column("jobs", "error_code")
