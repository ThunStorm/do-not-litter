from __future__ import annotations

from zhijian.db.models import AINote, AINoteSection, AINoteVersion, PlaceMention, Source, VideoAsset
from zhijian.services.video_note_search import (
    backfill_video_note_search_index,
    remove_video_note_search_index,
    search_video_note_ids,
    sync_video_note_search_index,
)


def test_video_note_search_indexes_title_body_sections_and_places(app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/search")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="昆明味觉旅行")
        db.add(asset)
        db.flush()
        note = AINote(video_asset_id=asset.id, status="COMPLETED")
        db.add(note)
        db.flush()
        version = AINoteVersion(
            ai_note_id=note.id,
            version=1,
            markdown="# 昆明\n\n菌子很鲜。",
            overview="正文出现但标题不出现的短语：菌子。",
            transcript_version=1,
        )
        db.add(version)
        db.flush()
        note.current_version_id = version.id
        db.add(
            AINoteSection(
                ai_note_version_id=version.id,
                ordinal=0,
                heading="文林街",
                body_markdown="两字短词测试",
                segment_ids_json=[],
            )
        )
        db.add(
            PlaceMention(
                video_asset_id=asset.id,
                name="篆新市场",
                suggested_name="篆新农贸市场",
            )
        )
        db.flush()
        sync_video_note_search_index(db, note, version, asset)
        db.commit()

        assert search_video_note_ids(db, "昆明")[0]["match_type"] == "标题命中"
        assert search_video_note_ids(db, "菌子")[0]["match_type"] == "正文命中"
        assert search_video_note_ids(db, "文林街")[0]["match_type"] == "章节命中"
        assert search_video_note_ids(db, "篆新农贸市场")[0]["match_type"] == "地点命中"
        assert search_video_note_ids(db, "!!") == []
        assert search_video_note_ids(db, "") == []
        assert backfill_video_note_search_index(db) == 1
        remove_video_note_search_index(db, note.id)
        assert search_video_note_ids(db, "昆明") == []
