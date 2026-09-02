from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

import zhijian.services.bilibili_auth as bilibili_auth
from zhijian.db.models import Job, JobStep
from zhijian.providers.media import MediaDownloadError, YtDlpMediaProvider
from zhijian.services.bilibili_auth import BilibiliLoginPoll


def _response(json: dict, *, cookies: bool = False) -> httpx.Response:
    headers = []
    if cookies:
        headers = [
            ("set-cookie", "SESSDATA=session-secret; Domain=.bilibili.com; Path=/"),
            ("set-cookie", "bili_jct=csrf-secret; Domain=.bilibili.com; Path=/"),
            ("set-cookie", "DedeUserID=123; Domain=.bilibili.com; Path=/"),
        ]
    return httpx.Response(
        200,
        json=json,
        headers=headers,
        request=httpx.Request("GET", "https://passport.bilibili.com/fixture"),
    )


def test_qr_login_extracts_and_verifies_cookie_without_echo(monkeypatch) -> None:
    responses = iter(
        [
            _response(
                {
                    "code": 0,
                    "data": {
                        "url": "https://passport.bilibili.com/h5-app/passport/login/scan?fixture=1",
                        "qrcode_key": "a" * 32,
                    },
                }
            ),
            _response({"code": 0, "data": {"code": 86101, "message": "未扫码"}}),
            _response({"code": 0, "data": {"code": 0, "message": ""}}, cookies=True),
            _response(
                {"code": 0, "data": {"isLogin": True, "uname": "测试用户", "mid": 123}}
            ),
        ]
    )
    monkeypatch.setattr(bilibili_auth, "_get", lambda *_args, **_kwargs: next(responses))

    started = bilibili_auth.start_bilibili_login(timeout=10)
    waiting = bilibili_auth.poll_bilibili_login(started["session_id"], timeout=10)
    completed = bilibili_auth.poll_bilibili_login(started["session_id"], timeout=10)

    assert waiting.status == "WAITING_SCAN"
    assert completed.status == "SUCCESS"
    assert completed.account_name == "测试用户"
    assert completed.cookie == "SESSDATA=session-secret; bili_jct=csrf-secret; DedeUserID=123"


def test_qr_login_api_stores_cookie_only_in_secret_store(
    monkeypatch, client, app_and_session
) -> None:
    _, factory = app_and_session
    cookie = "SESSDATA=session-secret; bili_jct=csrf-secret; DedeUserID=123"
    monkeypatch.setattr(
        "zhijian.api.router.start_bilibili_login",
        lambda **_kwargs: {
            "session_id": "login-fixture",
            "qr_url": "https://passport.bilibili.com/fixture",
            "expires_at": "2026-08-29T23:59:59Z",
            "status": "WAITING_SCAN",
        },
    )
    monkeypatch.setattr(
        "zhijian.api.router.poll_bilibili_login",
        lambda *_args, **_kwargs: BilibiliLoginPoll(
            "SUCCESS", "登录成功", cookie=cookie, account_name="测试用户", account_id="123"
        ),
    )

    initial = client.get("/api/settings/bilibili").json()
    started = client.post("/api/settings/bilibili/login")
    completed = client.get("/api/settings/bilibili/login/login-fixture")

    assert initial == {"cookie_saved": False, "account_name": None, "verified_at": None}
    assert started.status_code == 200
    assert completed.status_code == 200
    assert completed.json()["account_name"] == "测试用户"
    assert cookie not in completed.text
    secret_path = Path(factory.kw["bind"].url.database).parent / "secrets" / "video-bilibili-cookie"
    assert secret_path.read_text(encoding="utf-8") == cookie


def test_bilibili_412_is_classified_as_login_required(monkeypatch, tmp_path) -> None:
    class FakeYtDlp:
        def __init__(self, _options):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def extract_info(self, _url, download):
            assert download is True
            raise RuntimeError("HTTP Error 412: Precondition Failed")

    monkeypatch.setitem(sys.modules, "yt_dlp", SimpleNamespace(YoutubeDL=FakeYtDlp))

    with pytest.raises(MediaDownloadError) as raised:
        YtDlpMediaProvider(tmp_path, max_bytes=1024, timeout=10).download_video(
            "https://www.bilibili.com/video/BV1fixture"
        )

    assert raised.value.code == "VIDEO_LOGIN_REQUIRED"


def test_login_blocked_screenshot_can_be_skipped_but_required_audio_cannot(
    client, app_and_session
) -> None:
    _, factory = app_and_session
    with factory() as db:
        screenshot_job = Job(
            job_type="TRAVEL",
            status="NEEDS_USER",
            current_step="DOWNLOAD_VIDEO_FOR_FRAMES",
            progress=94,
            payload_json={},
            error_code="VIDEO_LOGIN_REQUIRED",
            error="请重新登录",
        )
        audio_job = Job(
            job_type="TRAVEL",
            status="NEEDS_USER",
            current_step="DOWNLOAD_AUDIO",
            progress=30,
            payload_json={},
            error_code="VIDEO_LOGIN_REQUIRED",
            error="请重新登录",
        )
        db.add_all([screenshot_job, audio_job])
        db.flush()
        db.add_all(
            [
                JobStep(
                    job_id=screenshot_job.id,
                    step_name="DOWNLOAD_VIDEO_FOR_FRAMES",
                    status="FAILED",
                ),
                JobStep(job_id=audio_job.id, step_name="DOWNLOAD_AUDIO", status="FAILED"),
            ]
        )
        db.commit()
        screenshot_job_id, audio_job_id = screenshot_job.id, audio_job.id

    screenshot_options = client.get(f"/api/jobs/{screenshot_job_id}/replay-options").json()
    audio_options = client.get(f"/api/jobs/{audio_job_id}/replay-options").json()
    skipped = client.post(f"/api/jobs/{screenshot_job_id}/skip-login-step")

    assert screenshot_options["login_required"] is True
    assert screenshot_options["skip_step_available"] is True
    assert audio_options["login_required"] is True
    assert audio_options["step_replay_available"] is True
    assert audio_options["replay_from_step"] == "DOWNLOAD_AUDIO"
    assert audio_options["skip_step_available"] is False
    assert skipped.status_code == 200
    with factory() as db:
        queued = db.get(Job, screenshot_job_id)
        assert queued and queued.status == "QUEUED"
        assert queued.payload_json["skip_login_step"] == "DOWNLOAD_VIDEO_FOR_FRAMES"
