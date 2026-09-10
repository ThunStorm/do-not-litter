from __future__ import annotations

import httpx
import pytest

from zhijian.core.url_policy import HttpsHostPolicy
from zhijian.resolvers.video.bilibili import (
    BilibiliResolver,
    SubtitleTrack,
    VideoResolveError,
    _subtitle_priority,
    first_usable_subtitle,
)
from zhijian.services.video_cover import normalize_cover_url


def test_https_host_policy_supports_safe_cdn_growth_without_similar_domain_bypass() -> None:
    policy = HttpsHostPolicy(
        exact_hosts=frozenset({"api.bilibili.com"}),
        host_suffixes=frozenset({"hdslb.com"}),
    )

    assert policy.allows("https://api.bilibili.com/x/player/v2")
    assert policy.allows("https://aisubtitle.hdslb.com/bfs/subtitle/example.json")
    assert policy.allows("https://hdslb.com/example.json")
    assert not policy.allows("http://aisubtitle.hdslb.com/example.json")
    assert not policy.allows("https://evilhdslb.com/example.json")
    assert not policy.allows("https://hdslb.com.evil.example/example.json")
    assert not policy.allows("https://hdslb.com@evil.example/example.json")
    assert not policy.allows("https://aisubtitle.hdslb.com:8443/example.json")


def test_cover_and_subtitle_cdn_use_the_shared_policy(monkeypatch) -> None:
    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def get(self, url, **_kwargs):
            return httpx.Response(
                200,
                json={"body": [{"content": "字幕", "from": 0, "to": 1}]},
                request=httpx.Request("GET", url),
            )

    monkeypatch.setattr("zhijian.resolvers.video.bilibili.httpx.Client", FakeClient)
    resolver = BilibiliResolver()

    segments = resolver.fetch_subtitle_segments(
        SubtitleTrack("https://aisubtitle.hdslb.com/bfs/subtitle/test.json", "ai-zh", "中文")
    )

    assert segments[0]["text"] == "字幕"
    assert normalize_cover_url("//i0.hdslb.com/bfs/archive/test.jpg") == (
        "https://i0.hdslb.com/bfs/archive/test.jpg"
    )
    with pytest.raises(VideoResolveError, match="外部访问目标不在许可范围"):
        resolver.fetch_subtitle_segments(
            SubtitleTrack("https://hdslb.com.evil.example/test.json", "ai-zh", "中文")
        )


def test_subtitle_priority_and_fallback_handle_platform_language_variants() -> None:
    tracks = [
        SubtitleTrack("https://a.hdslb.com/ar", "ai-ar", "阿拉伯语（自动生成）"),
        SubtitleTrack("https://a.hdslb.com/ai-zh", "ai-zh", "中文（自动生成）"),
        SubtitleTrack("https://a.hdslb.com/zh", "zh-CN", "中文"),
    ]
    ordered = sorted(tracks, key=_subtitle_priority)
    attempts: list[str] = []

    def fetch(track: SubtitleTrack) -> list[dict]:
        attempts.append(track.language)
        if track.language == "zh-CN":
            raise VideoResolveError("VIDEO_SUBTITLE_INVALID", "人工字幕暂不可用")
        return [{"text": "AI 中文字幕"}]

    selected, segments, failures = first_usable_subtitle(ordered, fetch)

    assert [track.language for track in ordered] == ["zh-CN", "ai-zh", "ai-ar"]
    assert attempts == ["zh-CN", "ai-zh"]
    assert selected and selected.language == "ai-zh"
    assert segments == [{"text": "AI 中文字幕"}]
    assert failures == [("zh-CN", "VIDEO_SUBTITLE_INVALID")]


def test_resolver_records_generated_track_and_uses_wbi_endpoint(monkeypatch) -> None:
    resolver = BilibiliResolver()
    requested: list[str] = []

    def get_json(url, _headers, **_kwargs):
        requested.append(url)
        return {
            "code": 0,
            "data": {
                "subtitle": {
                    "subtitles": [
                        {
                            "id_str": "track-fixture",
                            "lan": "ai-zh",
                            "lan_doc": "中文（自动生成）",
                            "subtitle_url": "https://aisubtitle.hdslb.com/bfs/subtitle/fixture.json",
                        }
                    ]
                }
            },
        }

    monkeypatch.setattr(resolver, "_get_json", get_json)
    tracks = resolver._fetch_subtitles("BV1fixture", "123", {})

    assert requested == ["https://api.bilibili.com/x/player/wbi/v2?bvid=BV1fixture&cid=123"]
    assert tracks[0].track_id == "track-fixture"
    assert tracks[0].generated is True
    assert tracks[0].source_kind == "BILIBILI_AI_SUBTITLE"


def test_login_required_subtitle_does_not_silently_fallback() -> None:
    track = SubtitleTrack("https://a.hdslb.com/zh", "ai-zh", "中文")

    with pytest.raises(VideoResolveError) as raised:
        first_usable_subtitle(
            [track],
            lambda _track: (_ for _ in ()).throw(
                VideoResolveError("VIDEO_LOGIN_REQUIRED", "登录失效")
            ),
        )

    assert raised.value.code == "VIDEO_LOGIN_REQUIRED"
