"""Add step replay artifacts and structured reading fields.

Revision ID: 0007
Revises: 0006
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "job_step_artifacts" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "job_step_artifacts",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("job_id", sa.String(64), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_name", sa.String(64), nullable=False),
        sa.Column("artifact_type", sa.String(64), nullable=False),
        sa.Column("artifact_ref_json", sa.JSON(), nullable=False),
        sa.Column("input_hash", sa.String(128)),
        sa.Column("content_hash", sa.String(128)),
        sa.Column("schema_version", sa.String(32), nullable=False),
        sa.Column("producer_version", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("replayable_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("invalidated_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("job_id", "step_name", "artifact_type", name="uq_job_step_artifact"),
    )
    op.create_index(
        "ix_job_step_artifacts_expiry", "job_step_artifacts", ["status", "replayable_until"]
    )
    with op.batch_alter_table("ai_note_sections") as batch:
        batch.add_column(sa.Column("thesis", sa.String(500), nullable=False, server_default=""))
        batch.add_column(sa.Column("summary", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("bullets_json", sa.JSON(), nullable=False, server_default="[]"))
        batch.add_column(sa.Column("anchor_id", sa.String(96), nullable=False, server_default=""))
    with op.batch_alter_table("video_screenshots") as batch:
        batch.add_column(sa.Column("caption", sa.String(500), nullable=False, server_default=""))
        batch.add_column(sa.Column("content_role", sa.String(64), nullable=False, server_default="KEY_FRAME"))
    op.execute("UPDATE ai_note_sections SET anchor_id = 'section-' || id WHERE anchor_id = ''")


def downgrade() -> None:
    with op.batch_alter_table("video_screenshots") as batch:
        batch.drop_column("content_role")
        batch.drop_column("caption")
    with op.batch_alter_table("ai_note_sections") as batch:
        batch.drop_column("anchor_id")
        batch.drop_column("bullets_json")
        batch.drop_column("summary")
        batch.drop_column("thesis")
    op.drop_index("ix_job_step_artifacts_expiry", table_name="job_step_artifacts")
    op.drop_table("job_step_artifacts")
