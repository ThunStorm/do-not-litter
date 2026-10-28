"""Bind each new note version to the exact Grounded Map used to generate it.

Revision ID: 0027
Revises: 0026

Unknown historical associations remain NULL; never infer them from creation time.
SQLite supports this nullable inline reference without rebuilding the note table.
"""

from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE ai_note_versions ADD COLUMN grounded_map_artifact_id VARCHAR(64) "
        "REFERENCES grounded_map_artifacts(id) ON DELETE SET NULL"
    )


def downgrade() -> None:
    op.drop_column("ai_note_versions", "grounded_map_artifact_id")
