from test_poi_review_contract import make_mention

from zhijian.db.models import Job, JobStep, PlaceMention
from zhijian.services.review_projection import review_projection


def test_projection_counts_identity_wait_and_resolves_without_queue(app_and_session, client):
    _, factory = app_and_session
    with factory() as db:
        job = Job(job_type="TRAVEL", status="PARTIAL_SUCCESS", payload_json={})
        db.add(job)
        db.commit()
        mention = make_mention(db)
        mention.submission_job_id = job.id
        mention.resolution_status = "REVIEW"
        other = PlaceMention(
            video_asset_id=mention.video_asset_id, name="其他地点", raw_name="其他地点", poi_policy="RESOLVE"
        )
        db.add(other)
        other.submission_job_id = job.id
        other.resolution_status = "UNRESOLVED"
        wait = Job(job_type="TRAVEL", status="QUEUED", payload_json={"localmux_cooldown_resume": {}})
        db.add(wait)
        db.commit()
        result = review_projection(db, "MANUAL")
        assert result["task_count"] == 1
        assert result["issue_count"] == 2
        assert len({i["key"] for i in result["issues"]}) == 2
        assert result["waiting_issue_count"] == 1
        assert review_projection(db, "WAIT")["issue_count"] == 1
        mention.resolution_status = "CONFIRMED"
        db.commit()
        assert review_projection(db, "MANUAL")["issue_count"] == 1
        assert job.status == "PARTIAL_SUCCESS"
    assert client.get("/api/review-issues?mode=bad").status_code == 422


def test_multiple_failed_steps_dont_duplicate_job_failure(app_and_session):
    _, factory = app_and_session
    with factory() as db:
        job = Job(job_type="TRAVEL", status="NEEDS_USER", payload_json={}, error_code="VIDEO_LOGIN_REQUIRED")
        db.add(job)
        db.flush()
        db.add_all([JobStep(job_id=job.id, step_name=n, status="FAILED") for n in ["FETCH_SUBTITLE", "ASR"]])
        db.commit()
        result = review_projection(db)
        assert result["task_count"] == 1
        assert result["issue_count"] == 2
        assert {i["reason"] for i in result["issues"]} == {"VIDEO_LOGIN_REQUIRED"}
        assert all(i["href"] == f"/tasks/{job.id}" for i in result["issues"])


def test_version_guard_never_falls_through_to_latest(app_and_session, client):
    from zhijian.db.models import AINote, AINoteVersion

    _, factory = app_and_session
    with factory() as db:
        mention = make_mention(db)
        note = AINote(video_asset_id=mention.video_asset_id)
        db.add(note)
        db.flush()
        old = AINoteVersion(ai_note_id=note.id, version=1, markdown="旧证据", transcript_version=1)
        latest = AINoteVersion(ai_note_id=note.id, version=2, markdown="新证据", transcript_version=2)
        db.add_all([old, latest])
        db.flush()
        note.current_version_id = latest.id
        db.commit()
        assert client.get(f"/api/video-notes/{note.id}?version_id={old.id}").status_code == 410
        assert client.get(f"/api/video-notes/{old.id}").status_code == 410
        assert client.get(f"/api/video-notes/{note.id}?version_id=deleted").status_code == 410
