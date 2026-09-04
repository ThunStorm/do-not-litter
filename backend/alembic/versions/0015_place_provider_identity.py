"""Enforce one canonical Place for each external POI.

Revision ID: 0015
Revises: 0014
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    duplicates = bind.execute(sa.text("""
        SELECT external_provider, external_poi_id, MIN(id) AS canonical_id
        FROM places
        WHERE external_provider IS NOT NULL AND external_poi_id IS NOT NULL
        GROUP BY lower(external_provider), external_poi_id
        HAVING COUNT(*) > 1
    """)).mappings().all()
    for duplicate in duplicates:
        ids = [row[0] for row in bind.execute(sa.text("""
            SELECT id FROM places
            WHERE lower(external_provider) = lower(:provider) AND external_poi_id = :poi
            ORDER BY created_at, id
        """), {"provider": duplicate["external_provider"], "poi": duplicate["external_poi_id"]}).all()]
        canonical, extras = ids[0], ids[1:]
        for extra in extras:
            for table in ("place_mentions", "place_insight_items", "place_observations"):
                bind.execute(
                    sa.text(f"UPDATE {table} SET place_id = :canonical WHERE place_id = :extra"),
                    {"canonical": canonical, "extra": extra},
                )
            bind.execute(sa.text("""
                DELETE FROM route_draft_items
                WHERE place_id = :extra AND route_draft_id IN
                    (SELECT route_draft_id FROM route_draft_items WHERE place_id = :canonical)
            """), {"canonical": canonical, "extra": extra})
            bind.execute(
                sa.text("UPDATE route_draft_items SET place_id = :canonical WHERE place_id = :extra"),
                {"canonical": canonical, "extra": extra},
            )
            for table in ("map_marker_states", "place_user_overlays", "place_user_notes"):
                bind.execute(
                    sa.text(
                        f"DELETE FROM {table} WHERE place_id = :extra AND "
                        f"EXISTS (SELECT 1 FROM {table} keep WHERE keep.place_id = :canonical)"
                    ),
                    {"canonical": canonical, "extra": extra},
                )
                bind.execute(
                    sa.text(f"UPDATE {table} SET place_id = :canonical WHERE place_id = :extra"),
                    {"canonical": canonical, "extra": extra},
                )
            bind.execute(sa.text("DELETE FROM places WHERE id = :extra"), {"extra": extra})
    op.create_index("uq_place_provider_poi", "places", ["external_provider", "external_poi_id"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_place_provider_poi", table_name="places")
