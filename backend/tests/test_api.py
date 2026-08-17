from __future__ import annotations

from io import BytesIO

from docx import Document
from sqlalchemy import select

from zhijian.db.models import Job, Setting
from zhijian.services.pipeline import process_job


def test_health(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_map_overview_switches_selected_preview(client) -> None:
    response = client.get("/api/travel/map?city=厦门市")
    assert response.status_code == 200
    overview = response.json()
    assert overview["coordinate_system"] == "GCJ02"
    assert overview["total_places"] >= 8
    target = overview["markers"][3]

    selected = client.get(f"/api/travel/map?city=厦门市&selected_place_id={target['id']}")
    assert selected.status_code == 200
    assert selected.json()["selected_place_id"] == target["id"]
    assert selected.json()["selected_preview"]["name"] == target["name"]


def test_route_draft_preserves_manual_order(client) -> None:
    markers = client.get("/api/travel/map?city=厦门市").json()["markers"]
    ordered_ids = [markers[2]["id"], markers[0]["id"], markers[1]["id"]]
    response = client.post(
        "/api/travel/route-drafts",
        json={"name": "步行清单", "city": "厦门市", "place_ids": ordered_ids},
    )
    assert response.status_code == 200
    assert [place["id"] for place in response.json()["places"]] == ordered_ids
    assert "distance" not in response.json()


def test_capture_text_runs_deterministic_pipeline(client, app_and_session) -> None:
    _, factory = app_and_session
    response = client.post(
        "/api/capture",
        json={
            "title": "北京市事业单位招聘公告",
            "text": "招聘 12 个岗位，本科及以上。报名截止 2026年9月3日 17:00。",
        },
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    with factory() as db:
        job = db.scalar(select(Job).where(Job.id == job_id))
        assert job is not None
        process_job(db, job)

    detail = client.get(f"/api/jobs/{job_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "COMPLETED"
    assert detail.json()["progress"] == 100

    with client.websocket_connect(f"/api/jobs/{job_id}/stream") as websocket:
        event = websocket.receive_json()
        assert event["type"] == "job.progress"
        assert event["id"] == job_id
        assert event["progress"] == 100


def test_provider_configuration_keeps_key_out_of_database(client, app_and_session) -> None:
    _, factory = app_and_session
    response = client.put(
        "/api/settings/providers/default",
        json={
            "provider": "DeepSeek",
            "base_url": "https://api.deepseek.com/v1",
            "model": "deepseek-chat",
            "api_key": "test-key-not-for-network",
        },
    )
    assert response.status_code == 200
    assert response.json()["api_key_saved"] is True

    with factory() as db:
        setting = db.get(Setting, "provider:default")
        assert setting is not None
        assert "test-key" not in str(setting.value_json)


def test_docx_upload_enters_the_same_durable_pipeline(client, app_and_session) -> None:
    _, factory = app_and_session
    document = Document()
    document.add_heading("北京市事业单位公开招聘", level=1)
    document.add_paragraph("本科及以上，报名截止 2026年9月3日 17:00。")
    payload = BytesIO()
    document.save(payload)

    response = client.post(
        "/api/capture/file",
        files={
            "upload": (
                "北京事业单位公告.docx",
                payload.getvalue(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert response.status_code == 200
    with factory() as db:
        job = db.get(Job, response.json()["job_id"])
        assert job is not None
        process_job(db, job)
        assert job.status == "COMPLETED"


def test_generic_file_is_reclassified_after_text_extraction(client, app_and_session) -> None:
    _, factory = app_and_session
    response = client.post(
        "/api/capture/file",
        files={"upload": ("notice.txt", "北京市事业单位招聘，本科及以上。", "text/plain")},
    )
    assert response.status_code == 200
    assert response.json()["job_type"] == "UNKNOWN"

    with factory() as db:
        job = db.get(Job, response.json()["job_id"])
        assert job is not None
        process_job(db, job)
        assert job.job_type == "RECRUITMENT"
        assert job.result_content_id is not None
