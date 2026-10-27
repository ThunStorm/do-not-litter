"""Scope destination identity by its administrative parents.

Revision ID: 0026
Revises: 0025
"""

import sqlalchemy as sa

from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("destinations") as batch:
        batch.drop_constraint("uq_destination_scope_name", type_="unique")
        batch.create_unique_constraint(
            "uq_destination_scope_region", ["scope_type", "canonical_name", "province", "city", "district"]
        )


def downgrade() -> None:
    duplicates = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT 1 FROM destinations GROUP BY scope_type, canonical_name HAVING count(*) > 1 LIMIT 1"
            )
        )
        .first()
    )
    if duplicates:
        raise RuntimeError("cannot downgrade: different regions share a destination name")
    with op.batch_alter_table("destinations") as batch:
        batch.drop_constraint("uq_destination_scope_region", type_="unique")
        batch.create_unique_constraint("uq_destination_scope_name", ["scope_type", "canonical_name"])
