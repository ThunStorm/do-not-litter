import hashlib
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from zhijian.core.config import Settings
from zhijian.core.storage import storage_ref
from zhijian.db.models import Job, JobStepArtifact, Source, VideoAsset, VideoCoverAsset
from zhijian.services import cover_text
from zhijian.services.temporal_context import validate_applications


def region(text, confidence=1, y=0.5):
    return {"text": text, "confidence": confidence, "bbox": [0.1, y, 0.8, 0.15]}


def payload(text):
    return {
        "identity": "a" * 64,
        "cover_id": "cover",
        "cover_hash": "b" * 64,
        "status": "READY",
        "regions": [region(text)],
    }


@pytest.mark.parametrize(
    "text,positive",
    [("8月份宝藏目的地推荐！", True), ("8月不推荐去草原", False), ("没有文字中的日期", False)],
)
def test_cover_metadata_never_creates_transcript_segments(text, positive):
    contexts = cover_text.cover_contexts(payload(text))
    assert bool(contexts and contexts[0]["intent"] == "RECOMMENDED") == positive
    if contexts:
        assert contexts[0]["segment_ids"] == [] and contexts[0]["source_kind"] == "COVER_TEXT"
        seg = SimpleNamespace(id="s", snapshot_id="snapshot", text="推荐甲地", corrected_text="")
        entity = {
            "entity_id": "e",
            "name": "甲地",
            "subject_role": "PRIMARY",
            "visit_intent": "RECOMMENDED",
            "poi_policy": "RESOLVE",
            "content_unit_id": "u",
            "temporal_applications": [
                {
                    "context_id": contexts[0]["context_id"],
                    "relation": "INCLUDED",
                    "segment_ids": ["s"],
                    "supporting_quote": "推荐甲地",
                }
            ],
        }
        units = [
            {
                "content_unit_id": "u",
                "unit_type": "PLACE_GUIDE",
                "anchor_entity_ids": ["e"],
                "segment_ids": ["s"],
            }
        ]
        assert bool(validate_applications(entity, units, contexts, [seg])) == positive


@pytest.mark.parametrize(
    "rows,status",
    [
        ([], "NO_TEXT"),
        ([region("8月推荐", 0.3)], "NEEDS_REVIEW"),
        ([region("8月推荐"), region("9月推荐", y=0.2)], "NEEDS_REVIEW"),
        ([region("8月份目的地推荐")], "READY"),
    ],
)
def test_quality_preserves_low_confidence_and_ambiguous_dates(rows, status):
    assert cover_text.quality(rows) == status


def test_malformed_boxes_reject_nonfinite_and_out_of_image():
    for box in [[0, 0, 2, 1], [0, 0, float("nan"), 1], [0, 0, 0, 1]]:
        with pytest.raises(ValueError):
            cover_text.normalize_regions([{**region("字"), "bbox": box}])


def setup_cover(factory, tmp_path):
    settings = Settings(_env_file=None, data_dir=tmp_path, secret_store="file")
    settings.ensure_directories()
    with factory() as db:
        source = Source(source_type="URL", locator="fixture://cover")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="fixture")
        db.add(asset)
        db.flush()
        path = settings.permanent_dir / (hashlib.sha256(b"fixture-cover-original").hexdigest() + ".jpg")
        path.write_bytes(b"fixture-cover-original")
        cover = VideoCoverAsset(
            video_asset_id=asset.id, status="READY", local_path=storage_ref(path, settings)
        )
        db.add(cover)
        db.commit()
        return settings, asset.id, path


def test_ocr_cache_and_worker_artifact_have_immutable_image_identity(app_and_session, tmp_path, monkeypatch):
    _, factory = app_and_session
    settings, aid, path = setup_cover(factory, tmp_path)
    calls = []
    monkeypatch.setattr(cover_text, "_ocr", lambda *args: calls.append(1) or [region("8月份目的地推荐")])
    monkeypatch.setattr(cover_text, "_vision", lambda *args: pytest.fail("default OCR must not call vision"))
    with factory() as db:
        asset = db.get(VideoAsset, aid)
        job = Job(job_type="TRAVEL", status="RUNNING", payload_json={})
        db.add(job)
        db.commit()
        first = cover_text.extract_cover_text(db, settings, asset, job)
        again = cover_text.extract_cover_text(db, settings, asset, job)
        assert calls == [1] and again["cache_hit"]
        assert (
            db.scalar(select(JobStepArtifact).where(JobStepArtifact.job_id == job.id)).input_hash
            == first["identity"]
        )
        new_hash = hashlib.sha256(b"changed-cover-original").hexdigest()
        new_path = path.with_name(new_hash + ".jpg")
        new_path.write_bytes(b"changed-cover-original")
        cover = db.scalar(select(VideoCoverAsset).where(VideoCoverAsset.video_asset_id == aid))
        cover.local_path = storage_ref(new_path, settings)
        cover.content_hash = new_hash
        db.commit()
        new = cover_text.extract_cover_text(db, settings, asset, job)
        assert new["identity"] != first["identity"] and new["cover_hash"] != first["cover_hash"]
        assert list((settings.permanent_dir / "cover-text" / first["identity"]).glob("*.json"))


def test_visual_failure_keeps_ocr_and_does_not_block_body(app_and_session, tmp_path, monkeypatch):
    _, factory = app_and_session
    settings, aid, _ = setup_cover(factory, tmp_path)
    monkeypatch.setattr(cover_text, "_ocr", lambda *args: [region("8月份目的地推荐")])

    def fail(*args):
        raise ValueError("interface unavailable")

    monkeypatch.setattr(cover_text, "_vision", fail)
    with factory() as db:
        result = cover_text.extract_cover_text(
            db, settings, db.get(VideoAsset, aid), allow_visual=True, force_visual=True
        )
        assert result["method"] == "OCR" and result["status"] == "READY" and result["vision_error_code"]
        assert result["contexts"][0]["raw_time_text"] == "8月份"


def test_cancel_during_ocr_propagates(app_and_session, tmp_path, monkeypatch):
    from zhijian.services.jobs import JobCancelled

    _, factory = app_and_session
    settings, aid, _ = setup_cover(factory, tmp_path)

    def cancel(*args):
        raise JobCancelled("cancelled")

    monkeypatch.setattr(cover_text, "_ocr", cancel)
    with factory() as db, pytest.raises(JobCancelled):
        cover_text.extract_cover_text(db, settings, db.get(VideoAsset, aid))


def test_named_vision_edges_have_explicit_coordinate_conversion():
    row = {
        "text": "8月推荐",
        "confidence": 0.9,
        "bounds": {"left": 0.1, "top": 0.2, "right": 0.9, "bottom": 0.4},
    }
    r = cover_text.normalize_regions([row], vision=True)[0]
    assert r["bbox"] == pytest.approx([0.1, 0.6, 0.8, 0.2])
    with pytest.raises(ValueError):
        cover_text.normalize_regions([region("8月推荐")], vision=True)


def test_edition_decoration_does_not_become_a_geographic_scope():
    p = payload("8月份宝藏目的地推荐！")
    p["regions"] += [region("人少景美又避暑", y=0.7), region("第xx弹", y=0.2)]
    contexts = cover_text.cover_contexts(p)
    assert contexts[0]["scope_terms"] == [] and contexts[0]["raw_time_text"] == "8月份"


def test_queue_is_worker_only_and_get_never_applies_to_note(client, app_and_session, tmp_path, monkeypatch):
    from zhijian.db.models import AINote
    from zhijian.services.cover_text import process_cover_text_job

    _, factory = app_and_session
    settings, aid, _ = setup_cover(factory, tmp_path)
    with factory() as db:
        note = AINote(video_asset_id=aid)
        db.add(note)
        db.commit()
        nid = note.id
    monkeypatch.setattr(cover_text, "_ocr", lambda *args: pytest.fail("API must not run OCR"))
    queued = client.post(f"/api/video-notes/{nid}/cover-text")
    assert queued.status_code == 200
    assert client.get(f"/api/video-notes/{nid}/cover-text").json()["applied_to_current_note"] is False
    monkeypatch.setattr(cover_text, "_ocr", lambda *args: [region("8月份目的地推荐")])
    with factory() as db:
        job = db.get(Job, queued.json()["job_id"])
        process_cover_text_job(db, job, settings)
        assert job.status == "COMPLETED"
        assert db.get(AINote, nid).current_version_id is None


def test_note_projection_appends_version_and_preserves_old_section_identity(app_and_session, tmp_path):
    from zhijian.db.models import (
        AINote,
        AINoteSection,
        AINoteVersion,
        GroundedMapArtifact,
        PlaceMention,
        Transcript,
    )
    from zhijian.services.temporal_replay import append_projection_note_version

    _, factory = app_and_session
    _, aid, _ = setup_cover(factory, tmp_path)
    with factory() as db:
        transcript = Transcript(video_asset_id=aid, version=1, source_kind="ASR")
        note = AINote(video_asset_id=aid)
        db.add_all([transcript, note])
        db.flush()
        values = dict(
            video_asset_id=aid,
            transcript_id=transcript.id,
            transcript_version=1,
            content_hash="same",
            prompt_version="test",
            supplement_hash="",
            provider="fixture",
            model="fixture",
        )
        original = GroundedMapArtifact(**values, semantic_hash="original")
        derived = GroundedMapArtifact(**values, semantic_hash="derived")
        db.add_all([original, derived])
        db.flush()
        source = AINoteVersion(
            ai_note_id=note.id,
            version=1,
            markdown="原模型正文",
            transcript_version=1,
            grounded_map_artifact_id=original.id,
        )
        db.add(source)
        db.flush()
        note.current_version_id = source.id
        old = PlaceMention(
            video_asset_id=aid,
            ai_note_version_id=source.id,
            name="甲地",
            metadata_json={"semantic": {"entity_id": "e"}},
        )
        new = PlaceMention(video_asset_id=aid, name="甲地", metadata_json={"semantic": {"entity_id": "e"}})
        db.add_all([old, new])
        db.flush()
        section = AINoteSection(
            ai_note_version_id=source.id,
            ordinal=0,
            heading="甲地",
            body_markdown="原段落",
            place_mention_ids_json=[old.id],
        )
        db.add(section)
        db.commit()
        result = append_projection_note_version(db, note, source, derived, [new])
        assert result.version == 2 and source.grounded_map_artifact_id == original.id
        assert source.markdown == result.markdown == "原模型正文" and old.ai_note_version_id == source.id
        assert new.ai_note_version_id == result.id and note.current_version_id == result.id
        new_section = db.scalar(select(AINoteSection).where(AINoteSection.ai_note_version_id == result.id))
        assert new_section.id != section.id and new_section.place_mention_ids_json == [new.id]
        assert section.place_mention_ids_json == [old.id]
        with pytest.raises(ValueError):
            append_projection_note_version(db, note, source, derived, [new])


def test_worker_preserves_run_fence_and_releases_finished_lease(app_and_session, tmp_path, monkeypatch):
    from zhijian.core.time import utc_now

    _, factory = app_and_session
    settings, aid, _ = setup_cover(factory, tmp_path)
    monkeypatch.setattr(cover_text, "_ocr", lambda *args: [region("8月目的地推荐")])
    with factory() as db:
        started = utc_now()
        job = Job(
            job_type="TRAVEL",
            status="RUNNING",
            lease_owner="worker-test",
            started_at=started,
            payload_json={"cover_text_video_asset_id": aid},
        )
        db.add(job)
        db.commit()
        original = job.started_at
        cover_text.process_cover_text_job(db, job, settings)
        assert job.status == "COMPLETED" and job.started_at == original
        assert job.lease_owner is None and job.lease_expire_at is None


def test_dense_cover_remains_review_only_instead_of_expanding_model_context():
    rows = [region("8月推荐" + ("字" * 390), y=0.1) for _ in range(4)]
    assert cover_text.quality(rows) == "NEEDS_REVIEW"
    assert cover_text.cover_contexts({**payload(""), "regions": rows, "status": "NEEDS_REVIEW"}) == []
    with pytest.raises(ValueError):
        cover_text.normalize_regions(rows * 3)


def test_small_negative_stamp_cannot_be_dropped_by_primary_font_filter():
    rows = [
        region("8月份宝藏目的地推荐"),
        {"text": "封闭维修，不推荐前往", "confidence": 1, "bbox": [0.1, 0.2, 0.8, 0.04]},
    ]
    assert cover_text.quality(rows) == "NEEDS_REVIEW"
    assert cover_text.cover_contexts({**payload(""), "regions": rows}) == []


def test_probe_metadata_does_not_invalidate_ocr_or_semantic_content(app_and_session, tmp_path, monkeypatch):
    from zhijian.db.models import Setting

    _, factory = app_and_session
    settings, aid, _ = setup_cover(factory, tmp_path)
    calls = []
    monkeypatch.setattr(cover_text, "_ocr", lambda *args: calls.append(1) or [region("8月份目的地推荐")])
    monkeypatch.setattr(cover_text, "_vision", lambda *args: pytest.fail("clear OCR does not need vision"))
    with factory() as db:
        policy = Setting(
            key="ai-stage-policy:COVER_TEXT",
            value_json={"execution_mode": "LOCAL_ONLY", "local_profile_id": "test-profile"},
        )
        profile = Setting(
            key="model-profile:test-profile",
            value_json={
                "provider": "ollama",
                "model": "same",
                "modalities": ["image"],
                "probe_results": {"checked_at": "first"},
            },
        )
        db.add_all([policy, profile])
        db.commit()
        asset = db.get(VideoAsset, aid)
        first = cover_text.extract_cover_text(db, settings, asset, allow_visual=False)
        profile.value_json = {**profile.value_json, "probe_results": {"checked_at": "new"}}
        db.commit()
        same = cover_text.extract_cover_text(db, settings, asset, allow_visual=False)
        assert same["cache_hit"] and len(calls) == 1
        assert same["semantic_identity"] == first["semantic_identity"]
        enabled = cover_text.extract_cover_text(db, settings, asset, allow_visual=True)
        assert enabled["semantic_identity"] == first["semantic_identity"]
        profile.value_json = {**profile.value_json, "probe_results": {"checked_at": "third"}}
        db.commit()
        assert cover_text.extract_cover_text(db, settings, asset, allow_visual=True)["cache_hit"]


def test_semantic_review_cache_does_not_expire_into_paid_retry(app_and_session, tmp_path, monkeypatch):
    import json

    _, factory = app_and_session
    settings, aid, _ = setup_cover(factory, tmp_path)
    calls = []
    monkeypatch.setattr(
        cover_text,
        "_ocr",
        lambda *args: calls.append(1) or [region("8月推荐甲地"), region("9月推荐乙地", y=0.2)],
    )
    with factory() as db:
        first = cover_text.extract_cover_text(db, settings, db.get(VideoAsset, aid))
        assert first["status"] == "NEEDS_REVIEW"
        path = settings.permanent_dir / "cover-text" / (first["identity"] + ".json")
        saved = json.loads(path.read_text())
        saved["expires_at"] = 0
        path.write_text(json.dumps(saved))
        assert cover_text.extract_cover_text(db, settings, db.get(VideoAsset, aid))["cache_hit"]
        assert len(calls) == 1
    assert not cover_text.stable_extraction_result(
        {"status": "NEEDS_REVIEW", "regions": [], "error_code": "OCR_FAILED"}
    )
    assert not cover_text.stable_extraction_result(
        {"status": "READY", "regions": [region("8月推荐")], "vision_error_code": "TIMEOUT"}
    )
