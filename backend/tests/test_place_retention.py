from __future__ import annotations

import pytest
from sqlalchemy import select

from zhijian.db.models import (
    AINote,
    AINoteVersion,
    ContentItem,
    Job,
    MapMarkerState,
    Place,
    PlaceInsightItem,
    PlaceMention,
    PlaceNoteVersion,
    PlaceUserNote,
    PlaceVisitWindow,
    Source,
    VideoAsset,
)


def setup_case(factory):
    with factory() as db:
        sources = [Source(source_type="URL", locator=f"https://example.test/retention/{i}") for i in range(2)]
        db.add_all(sources)
        db.flush()
        assets = [VideoAsset(source_id=s.id, canonical_url=s.locator) for s in sources]
        db.add_all(assets)
        db.flush()
        notes = [
            AINote(video_asset_id=a.id, submission_job_id=f"retention-job-{i}") for i, a in enumerate(assets)
        ]
        db.add_all(notes)
        db.flush()
        versions = [
            AINoteVersion(ai_note_id=n.id, version=1, markdown="# test", transcript_version=1) for n in notes
        ]
        db.add_all(versions)
        db.flush()
        for n, v in zip(notes, versions, strict=True):
            n.current_version_id = v.id
        places = [
            Place(name=name, place_type="景区", latitude=1, longitude=1) for name in ["专属", "共享", "人工"]
        ]
        db.add_all(places)
        db.flush()
        mentions = []
        for i, targets in enumerate([places, [places[1]]]):
            db.add(
                ContentItem(
                    content_type="VIDEO_NOTE",
                    source_id=sources[i].id,
                    title=f"note-{i}",
                    structured_json={"note_id": notes[i].id},
                )
            )
            for p in targets:
                m = PlaceMention(
                    video_asset_id=assets[i].id,
                    ai_note_version_id=versions[i].id,
                    submission_job_id=notes[i].submission_job_id,
                    name=p.name,
                    place_id=p.id,
                    reason=f"source-{i}",
                )
                db.add(m)
                db.flush()
                db.add_all(
                    [
                        PlaceInsightItem(
                            place_id=p.id,
                            place_mention_id=m.id,
                            source_id=sources[i].id,
                            insight_type="HIGHLIGHT",
                            value_text=f"source-{i}",
                            provenance="SOURCE_FACT",
                        ),
                        PlaceVisitWindow(
                            place_id=p.id,
                            place_mention_id=m.id,
                            source_id=sources[i].id,
                            month=i + 1,
                            provenance="THEME_CONTEXT",
                        ),
                    ]
                )
                mentions.append(m)
        db.add(PlaceUserNote(place_id=places[2].id, markdown="personal"))
        db.add(MapMarkerState(place_id=places[0].id))
        db.add(
            PlaceNoteVersion(
                place_id=places[1].id,
                version=1,
                markdown="stale-source-0",
                model_provider="deterministic",
                model_name="evidence-template",
            )
        )
        db.commit()
        return [s.id for s in sources], [n.id for n in notes], [p.id for p in places]


@pytest.mark.parametrize("entry", ["source", "note", "bulk-note"])
def test_deletion_cleans_owned_places_but_preserves_shared_and_personal(client, app_and_session, entry):
    _, factory = app_and_session
    sources, notes, places = setup_case(factory)
    if entry == "source":
        response = client.request(
            "DELETE", f"/api/sources/{sources[0]}/evidence-chain", json={"confirm": True}
        )
    elif entry == "note":
        response = client.delete(f"/api/video-notes/{notes[0]}")
    else:
        response = client.request("DELETE", "/api/video-notes/bulk", json={"ids": [notes[0]]})
    assert response.status_code == 200, response.text
    with factory() as db:
        assert db.get(Place, places[0]) is None
        assert db.get(Place, places[1]) is not None
        assert db.get(Place, places[2]) is not None
        assert db.get(AINote, notes[1]) is not None
        assert not db.scalars(
            select(PlaceMention).where(PlaceMention.video_asset_id.not_in(select(VideoAsset.id)))
        ).all()
        insights = db.scalars(select(PlaceInsightItem).where(PlaceInsightItem.place_id.in_(places))).all()
        assert [i.value_text for i in insights] == ["source-1"]
        windows = db.scalars(select(PlaceVisitWindow).where(PlaceVisitWindow.place_id.in_(places))).all()
        assert len(windows) == 1 and windows[0].month == 2
        latest = db.scalar(
            select(PlaceNoteVersion)
            .where(PlaceNoteVersion.place_id == places[1])
            .order_by(PlaceNoteVersion.version.desc())
        )
        assert latest and "source-0" not in latest.markdown
        assert (
            db.scalar(select(PlaceUserNote).where(PlaceUserNote.place_id == places[2])).markdown == "personal"
        )


def test_delete_one_note_keeps_same_video_other_submission(client, app_and_session):
    _, factory = app_and_session
    _, notes, places = setup_case(factory)
    with factory() as db:
        original = db.get(AINote, notes[0])
        sibling = AINote(video_asset_id=original.video_asset_id, submission_job_id="retention-sibling")
        db.add(sibling)
        db.flush()
        version = AINoteVersion(ai_note_id=sibling.id, version=1, markdown="# sibling", transcript_version=1)
        db.add(version)
        db.flush()
        sibling.current_version_id = version.id
        mention = PlaceMention(
            video_asset_id=sibling.video_asset_id,
            ai_note_version_id=version.id,
            submission_job_id=sibling.submission_job_id,
            name="shared",
            place_id=places[0],
        )
        db.add(mention)
        db.commit()
        sibling_id, mention_id = sibling.id, mention.id
    assert client.delete(f"/api/video-notes/{notes[0]}").status_code == 200
    with factory() as db:
        assert db.get(AINote, sibling_id)
        assert db.get(PlaceMention, mention_id)
        assert db.get(Place, places[0])
        assert db.get(PlaceMention, mention_id).ai_note_version_id is not None


def test_delete_respects_terminal_lease_and_rolls_back(client, app_and_session):
    _, factory = app_and_session
    sources, notes, places = setup_case(factory)
    with factory() as db:
        db.add(
            Job(
                job_type="TRAVEL",
                status="CANCELLED",
                lease_owner="still-running",
                payload_json={"source_id": sources[0]},
            )
        )
        db.commit()
    assert client.delete(f"/api/video-notes/{notes[0]}").status_code == 409
    with factory() as db:
        assert db.get(Place, places[0])
        assert db.get(AINote, notes[0])


def test_travel_category_includes_video_notes_without_changing_identity(client, app_and_session):
    _, factory = app_and_session
    _, _, _ = setup_case(factory)
    travel = client.get("/api/content?content_type=TRAVEL").json()
    video = client.get("/api/content?content_type=VIDEO_NOTE").json()
    hiring = client.get("/api/content?content_type=RECRUITMENT").json()
    assert len(video) == 2
    assert {v["id"] for v in video} <= {v["id"] for v in travel}
    assert all(v["content_type"] in {"TRAVEL", "VIDEO_NOTE"} for v in travel)
    assert all(v["content_type"] == "RECRUITMENT" for v in hiring)
    assert len(client.get("/api/content?content_type=VIDEO_NOTE&query=note-0").json()) == 1


def test_evidence_chain_cleans_legacy_content_only_place(client, app_and_session):
    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="TEXT", locator="legacy-place-owner")
        db.add(source)
        db.flush()
        content = ContentItem(source_id=source.id, content_type="TRAVEL", title="legacy")
        db.add(content)
        db.flush()
        place = Place(
            content_item_id=content.id, name="legacy place", place_type="景区", latitude=1, longitude=1
        )
        db.add(place)
        db.commit()
        source_id, place_id = source.id, place.id
    response = client.request("DELETE", f"/api/sources/{source_id}/evidence-chain", json={"confirm": True})
    assert response.status_code == 200
    with factory() as db:
        assert db.get(Place, place_id) is None


def test_bulk_delete_is_atomic_when_a_note_is_missing(client, app_and_session):
    _, factory = app_and_session
    _, notes, places = setup_case(factory)
    assert (
        client.request("DELETE", "/api/video-notes/bulk", json={"ids": [notes[0], "missing"]}).status_code
        == 404
    )
    with factory() as db:
        assert db.get(AINote, notes[0])
        assert db.get(Place, places[0])


def test_note_deletion_cleans_its_visual_facts_while_shared_video_remains(client, app_and_session):
    from zhijian.db.models import VideoScreenshot, VisualFact

    _, factory = app_and_session
    sources, notes, _ = setup_case(factory)
    with factory() as db:
        original = db.get(AINote, notes[0])
        sibling = AINote(video_asset_id=original.video_asset_id, submission_job_id="visual-sibling")
        place = Place(name="visual only", place_type="景区", latitude=1, longitude=1)
        db.add_all([sibling, place])
        db.flush()
        shot = VideoScreenshot(
            video_asset_id=original.video_asset_id,
            ai_note_version_id=original.current_version_id,
            planned_timestamp_ms=0,
        )
        db.add(shot)
        db.flush()
        fact = VisualFact(
            screenshot_id=shot.id,
            place_id=place.id,
            source_id=sources[0],
            fact_type="HIGHLIGHT",
            value="only in deleted note",
            confidence=0.9,
        )
        db.add(fact)
        db.commit()
        place_id, fact_id, sibling_id = place.id, fact.id, sibling.id
    assert client.delete(f"/api/video-notes/{notes[0]}").status_code == 200
    with factory() as db:
        assert db.get(AINote, sibling_id)
        assert db.get(Place, place_id) is None
        assert db.get(VisualFact, fact_id) is None


@pytest.mark.parametrize("entry", ["source", "note"])
def test_personal_insight_bound_to_deleted_mention_is_detached_not_cascaded(client, app_and_session, entry):
    _, factory = app_and_session
    sources, notes, places = setup_case(factory)
    with factory() as db:
        db.get(Place, places[2]).summary = "source-0"
        mention = db.scalar(select(PlaceMention).where(PlaceMention.place_id == places[2]))
        personal = PlaceInsightItem(
            place_id=places[2],
            place_mention_id=mention.id,
            source_id=sources[0],
            insight_type="OTHER",
            value_text="my own experience",
            provenance="USER_ADDED",
        )
        db.add(personal)
        db.commit()
        personal_id = personal.id
    if entry == "source":
        response = client.request(
            "DELETE", f"/api/sources/{sources[0]}/evidence-chain", json={"confirm": True}
        )
    else:
        response = client.delete(f"/api/video-notes/{notes[0]}")
    assert response.status_code == 200
    with factory() as db:
        item = db.get(PlaceInsightItem, personal_id)
        assert item and item.source_id is None and item.place_mention_id is None
        assert db.get(Place, places[2])
        assert db.get(Place, places[2]).summary == ""
