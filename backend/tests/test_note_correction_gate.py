"""Reading visibility follows the version-bound correction, not section formatting."""
from datetime import UTC, datetime

import pytest

from zhijian.db.models import (
    AINote,
    AINoteSection,
    AINoteVersion,
    Segment,
    Snapshot,
    Source,
    Transcript,
    VideoAsset,
)


@pytest.mark.parametrize(
    "status,coverage,segment_status,purged,summary,hidden",
    [
        ("CORRECTED", 1.0, "CORRECTED", False, "", False),
        ("PASS_THROUGH", 1.0, "UNCHANGED", False, "", False),
        ("UNCORRECTED", 0, "UNCORRECTED", False, "已有摘要", True),
        ("REVIEW", 0.5, "CORRECTED", False, "已有摘要", True),
        ("CORRECTED", 1.0, "UNCORRECTED", False, "", True),
        ("CORRECTED", 1.0, "CORRECTED", True, "", False),
    ],
)
def test_visibility_uses_bound_transcript(
    client, app_and_session, status, coverage, segment_status, purged, summary, hidden,
):
    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.com/video", title="测试")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="测试")
        snapshot = Snapshot(source_id=source.id, content_hash="fixture")
        db.add_all([asset, snapshot])
        db.flush()
        db.add(Segment(snapshot_id=snapshot.id, text="原文", correction_status=segment_status))
        db.add(Transcript(
            video_asset_id=asset.id, version=1, source_kind="ASR", segment_count=1,
            purged_at=datetime.now(UTC) if purged else None,
            metadata_json={"snapshot_id": snapshot.id, "correction_status": status,
                           "correction_coverage": coverage},
        ))
        # A newer transcript must never change the old note's quality decision.
        db.add(Transcript(
            video_asset_id=asset.id, version=2, source_kind="ASR", segment_count=1,
            metadata_json={"correction_status": "CORRECTED", "correction_coverage": 1.0},
        ))
        note = AINote(video_asset_id=asset.id, status="COMPLETED")
        db.add(note)
        db.flush()
        version = AINoteVersion(
            ai_note_id=note.id, version=1, transcript_version=1, markdown="正文",
            warnings_json=["证据要点待归纳"],
        )
        db.add(version)
        db.flush()
        note.current_version_id = version.id
        db.add(AINoteSection(
            ai_note_version_id=version.id, ordinal=0, heading="待归纳的证据要点",
            summary=summary, body_markdown="保留的证据正文", bullets_json=[],
        ))
        db.commit()
        note_id = note.id
    result = client.get(f"/api/video-notes/{note_id}").json()
    assert result["needs_regeneration"] is hidden
    assert result["sections"][0]["body_markdown"] == "保留的证据正文"
    assert result["warnings"] == ["证据要点待归纳"]
