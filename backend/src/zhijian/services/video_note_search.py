"""Deterministic SQLite FTS index for current Video Note versions."""
from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from zhijian.db.models import AINote, AINoteSection, AINoteVersion, PlaceMention, VideoAsset

_TABLE = "video_note_search"


def _create_fts_sql(tokenizer: str) -> str:
    return (
        "CREATE VIRTUAL TABLE IF NOT EXISTS video_note_search "
        "USING fts5(note_id UNINDEXED, version_id UNINDEXED, title, body, sections, places, "
        f"tokenize='{tokenizer}')"
    )


def ensure_video_note_search_index(db: Session) -> str:
    """Return the tokenizer in use; tests and fresh databases need no migration shortcut."""
    try:
        db.execute(
            text(
                _create_fts_sql("trigram")
            )
        )
        return "trigram"
    except Exception:
        db.execute(
            text(
                _create_fts_sql("unicode61")
            )
        )
        return "unicode61"


def sync_video_note_search_index(
    db: Session, note: AINote, version: AINoteVersion, asset: VideoAsset
) -> None:
    ensure_video_note_search_index(db)
    sections = db.scalars(
        select(AINoteSection)
        .where(AINoteSection.ai_note_version_id == version.id)
        .order_by(AINoteSection.ordinal)
    ).all()
    places = db.scalars(select(PlaceMention).where(PlaceMention.video_asset_id == asset.id)).all()
    section_text = "\n".join(
        f"{item.heading}\n{item.summary}\n{item.body_markdown}" for item in sections
    )
    db.execute(text("DELETE FROM video_note_search WHERE note_id = :note_id"), {"note_id": note.id})
    db.execute(
        text(
            "INSERT INTO video_note_search(note_id, version_id, title, body, sections, places) "
            "VALUES (:note_id, :version_id, :title, :body, :sections, :places)"
        ),
        {
            "note_id": note.id,
            "version_id": version.id,
            "title": asset.title,
            "body": version.markdown,
            "sections": section_text,
            "places": "\n".join(
                filter(None, (item.suggested_name or item.name for item in places))
            ),
        },
    )


def remove_video_note_search_index(db: Session, note_id: str) -> None:
    ensure_video_note_search_index(db)
    db.execute(text("DELETE FROM video_note_search WHERE note_id = :note_id"), {"note_id": note_id})


def search_video_note_ids(db: Session, query: str, limit: int = 100) -> list[dict[str, str]]:
    ensure_video_note_search_index(db)
    value = query.strip()
    if not value:
        return []
    # FTS5 trigram cannot match some two-character Chinese terms. Fall back to
    # deterministic LIKE across the indexed text columns for that narrow case.
    if len(value) < 3:
        rows = db.execute(
            text(
                "SELECT note_id, version_id, title, body, sections, places FROM video_note_search "
                "WHERE title LIKE :value OR body LIKE :value OR sections LIKE :value OR places LIKE :value "
                "LIMIT :limit"
            ),
            {"value": f"%{value}%", "limit": limit},
        ).mappings()
    else:
        escaped = '"' + value.replace('"', '""') + '"'
        rows = db.execute(
            text(
                "SELECT note_id, version_id, title, body, sections, places FROM video_note_search "
                "WHERE video_note_search MATCH :query ORDER BY rank LIMIT :limit"
            ),
            {"query": escaped, "limit": limit},
        ).mappings()
    return [_search_row(row, value) for row in rows]


def backfill_video_note_search_index(db: Session, notes: Iterable[AINote] | None = None) -> int:
    count = 0
    for note in notes or db.scalars(select(AINote).where(AINote.current_version_id.is_not(None))).all():
        version = db.get(AINoteVersion, note.current_version_id)
        asset = db.get(VideoAsset, note.video_asset_id)
        if version is None or asset is None:
            continue
        sync_video_note_search_index(db, note, version, asset)
        count += 1
    return count


def _search_row(row: dict, query: str) -> dict[str, str]:
    fields = (("title", "标题命中"), ("body", "正文命中"), ("sections", "章节命中"), ("places", "地点命中"))
    for field, label in fields:
        value = str(row[field] or "")
        position = value.find(query)
        if position >= 0:
            start = max(0, position - 36)
            end = min(len(value), position + len(query) + 72)
            return {
                "note_id": str(row["note_id"]),
                "version_id": str(row["version_id"]),
                "match_type": label,
                "snippet": value[start:end].replace("\n", " "),
            }
    return {
        "note_id": str(row["note_id"]),
        "version_id": str(row["version_id"]),
        "match_type": "正文命中",
        "snippet": "",
    }
