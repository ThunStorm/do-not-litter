from __future__ import annotations

from urllib.parse import parse_qs

import httpx
import pytest

from zhijian.db.models import Job, Source
from zhijian.resolvers.video.bilibili import BilibiliResolver, VideoResolveError, is_bilibili_url
from zhijian.resolvers.video.url_parser import parse_bilibili_url
from zhijian.services.input_normalizer import normalize_capture_input

BVID = "BV1Tvbe6EEw2"


@pytest.mark.parametrize("host", ["www.bilibili.com", "m.bilibili.com", "bilibili.com"])
@pytest.mark.parametrize("scheme", ["https://", "http://", ""])
def test_capture_accepts_common_bilibili_hosts_and_keeps_query(host, scheme):
    raw = f"{scheme}{host}/video/{BVID}/?p=3&share_source=copy_web#reply42"
    result = normalize_capture_input(f"【视频标题】\n{raw}，复制打开哔哩哔哩")
    assert result.selected_url == f"https://{host}/video/{BVID}/?p=3&share_source=copy_web#reply42"
    parsed = parse_bilibili_url(result.selected_url)
    assert (parsed.bvid, parsed.page_number) == (BVID, 3)
    assert not parsed.is_short


@pytest.mark.parametrize("raw", ["b23.tv/AbCd", "www.b23.tv/AbCd", "B23.TV/AbCd", "http://b23.tv/AbCd"])
def test_short_link_input_preserves_case_sensitive_code_and_parameters(raw):
    result = normalize_capture_input(f"分享 {raw}?p=2&share_medium=android 复制打开")
    assert result.selected_url in {
        "https://b23.tv/AbCd?p=2&share_medium=android",
        "https://www.b23.tv/AbCd?p=2&share_medium=android",
    }
    assert is_bilibili_url(result.selected_url)
    assert parse_bilibili_url(result.selected_url).is_short


def test_share_markdown_and_distinct_pages_preserve_capture_semantics():
    url = f"https://m.bilibili.com/video/{BVID}?p=2&t=13&x=%E4%B8%AD#reply"
    assert normalize_capture_input(f"[标题]({url})。<{url}>").candidates == (url,)
    assert normalize_capture_input(f"{url} {url.replace('p=2', 'p=3')}").kind == "MULTIPLE_URLS"
    assert normalize_capture_input(f"https://example.org/帮助 {url}").selected_url == url
    assert normalize_capture_input("user@b23.tv/code").kind == "TEXT_ONLY"
    assert normalize_capture_input("evilb23.tv/code").kind == "TEXT_ONLY"


def test_share_url_can_follow_chinese_text_and_contain_url_query_values():
    url = f"m.bilibili.com/video/{BVID}?p=2&from=https://example.org/a!b"
    assert normalize_capture_input(f"分享链接{url}。复制打开").selected_url == f"https://{url}"


@pytest.mark.parametrize(
    "url, bvid, aid",
    [
        (f"https://m.bilibili.com/video/{BVID}?p=2", BVID, None),
        (f"https://www.bilibili.com/s/video/{BVID}?p=2", BVID, None),
        ("https://www.bilibili.com/video/av170001/?p=2", None, "170001"),
        (f"https://player.bilibili.com/player.html?bvid={BVID}&p=2", BVID, None),
        ("https://player.bilibili.com/player.html?aid=170001&p=2", None, "170001"),
    ],
)
def test_parser_supports_video_and_player_identifiers(url, bvid, aid):
    parsed = parse_bilibili_url(url)
    assert (parsed.bvid, parsed.aid, parsed.page_number) == (bvid, aid, 2)


@pytest.mark.parametrize(
    "url",
    [
        "https://b23.tv.evil.example/code",
        "https://evilbilibili.com/video/BV1test",
        "https://b23.tv@evil.example/code",
        "https://name:secret@b23.tv/code",
        "https://b23.tv:8443/code",
        "https://127.0.0.1/code",
        "file://b23.tv/code",
        "https://[::1",
    ],
)
def test_parser_and_capture_routing_reject_unsafe_video_urls(url):
    assert not is_bilibili_url(url)
    with pytest.raises(ValueError):
        parse_bilibili_url(url)


def mock_transport(monkeypatch, handler):
    client_type = httpx.Client
    monkeypatch.setattr(
        "zhijian.resolvers.video.bilibili.httpx.Client",
        lambda **kwargs: client_type(transport=httpx.MockTransport(handler), **kwargs),
    )


@pytest.mark.parametrize(
    "target, id_query",
    [
        (f"https://m.bilibili.com/video/{BVID}?p=2&share=android", {"bvid": [BVID]}),
        ("https://www.bilibili.com/video/av170001?p=2", {"aid": ["170001"]}),
        (f"https://player.bilibili.com/player.html?bvid={BVID}&p=2", {"bvid": [BVID]}),
    ],
)
def test_short_redirect_to_video_resolves_canonical_identity_without_loading_page(
    monkeypatch, target, id_query
):
    requested = []

    def handler(request):
        requested.append(request)
        if request.url.host == "b23.tv":
            assert "cookie" not in request.headers
            return httpx.Response(302, headers={"location": target})
        assert request.url.host == "api.bilibili.com"
        if request.url.path.endswith("/view"):
            assert parse_qs(request.url.query.decode()) == id_query
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "bvid": BVID,
                        "aid": 170001,
                        "title": "视频",
                        "owner": {"name": "作者"},
                        "pages": [
                            {"cid": 101, "part": "第一P", "duration": 10},
                            {"cid": 102, "part": "第二P", "duration": 20},
                        ],
                    },
                },
            )
        return httpx.Response(200, json={"code": 0, "data": {"subtitle": {"subtitles": []}}})

    mock_transport(monkeypatch, handler)
    result = BilibiliResolver(max_redirects=1).resolve("https://b23.tv/code", cookie="fixture-cookie")
    assert result.canonical_url == f"https://www.bilibili.com/video/{BVID}?p=2"
    assert (result.bvid, result.cid, result.page_number, result.title) == (BVID, "102", 2, "第二P")
    assert len(requested) == 3


@pytest.mark.parametrize("target_suffix, expected", [("", 3), ("?p=2", 2)])
def test_short_link_page_falls_back_to_original_only_if_target_has_no_page(
    monkeypatch, target_suffix, expected
):
    mock_transport(
        monkeypatch,
        lambda req: httpx.Response(
            302,
            headers={"location": f"https://www.bilibili.com/video/{BVID}{target_suffix}"},
        ),
    )
    result = BilibiliResolver(max_redirects=1)._resolve_short_url("https://b23.tv/code?p=3")
    assert parse_bilibili_url(result).page_number == expected


def test_relative_short_redirect_chain_obeys_exact_hop_limit(monkeypatch):
    requested = []

    def handler(request):
        requested.append(str(request.url))
        target = "/next" if request.url.path == "/code" else f"https://m.bilibili.com/video/{BVID}"
        return httpx.Response(302, headers={"location": target})

    mock_transport(monkeypatch, handler)
    assert BilibiliResolver(max_redirects=2)._resolve_short_url("https://b23.tv/code").endswith(BVID)
    assert requested == ["https://b23.tv/code", "https://b23.tv/next"]


@pytest.mark.parametrize(
    "target",
    [
        "https://127.0.0.1/private",
        "https://192.168.1.1/private",
        "http://www.bilibili.com/video/BV1test",
        "https://bilibili.com.evil.example/video/BV1test",
        "https://name:secret@b23.tv/code",
        "https://b23.tv:8443/code",
        "file:///etc/passwd",
    ],
)
def test_short_redirect_is_validated_before_request(monkeypatch, target):
    requested = []

    def handler(request):
        requested.append(str(request.url))
        return httpx.Response(302, headers={"location": target})

    mock_transport(monkeypatch, handler)
    with pytest.raises(VideoResolveError) as err:
        BilibiliResolver()._resolve_short_url("https://b23.tv/code")
    assert err.value.code == "VIDEO_REDIRECT_BLOCKED"
    assert requested == ["https://b23.tv/code"]


@pytest.mark.parametrize(
    "status, location, code",
    [
        (404, None, "VIDEO_SHORT_URL_EXPIRED"),
        (410, None, "VIDEO_SHORT_URL_EXPIRED"),
        (200, None, "VIDEO_SHORT_URL_EXPIRED"),
        (302, None, "VIDEO_SHORT_URL_EXPIRED"),
        (503, None, "VIDEO_NETWORK_FAILED"),
        (302, "/loop", "VIDEO_TOO_MANY_REDIRECTS"),
    ],
)
def test_short_redirect_failures_are_stable(monkeypatch, status, location, code):
    requested = []

    def handler(request):
        requested.append(request)
        return httpx.Response(status, headers={"location": location} if location else {})

    mock_transport(monkeypatch, handler)
    with pytest.raises(VideoResolveError) as err:
        BilibiliResolver(max_redirects=2)._resolve_short_url("https://b23.tv/code")
    assert err.value.code == code
    assert len(requested) <= 2


def test_short_network_error_does_not_leak_query(monkeypatch):
    def handler(request):
        raise httpx.ConnectError(f"failed {request.url}", request=request)

    mock_transport(monkeypatch, handler)
    with pytest.raises(VideoResolveError) as err:
        BilibiliResolver()._resolve_short_url("https://b23.tv/code?private=fixture")
    assert err.value.code == "VIDEO_NETWORK_FAILED"
    assert "private" not in str(err.value)


@pytest.mark.parametrize(
    "text, selected",
    [
        (
            f"手机分享 m.bilibili.com/video/{BVID}?p=2&share_source=copy_link 复制打开",
            f"https://m.bilibili.com/video/{BVID}?p=2&share_source=copy_link",
        ),
        (
            "【分享】http://b23.tv/AbCd?share_medium=android 复制打开",
            "https://b23.tv/AbCd?share_medium=android",
        ),
        (
            f"player.bilibili.com/player.html?bvid={BVID}&p=2",
            f"https://player.bilibili.com/player.html?bvid={BVID}&p=2",
        ),
    ],
)
def test_api_capture_routes_common_links_to_video_job_without_network(
    client, app_and_session, monkeypatch, text, selected
):
    def no_network(*args, **kwargs):
        pytest.fail("Capture请求内不应访问网络")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", no_network)
    monkeypatch.setattr(BilibiliResolver, "resolve", no_network)
    _, factory = app_and_session
    response = client.post("/api/capture", json={"text": text})
    assert response.status_code == 200
    with factory() as db:
        source = db.get(Source, response.json()["source_id"])
        job = db.get(Job, response.json()["job_id"])
        assert source.locator == selected
        assert job.payload_json["locator"] == selected
        assert job.payload_json["video_platform"] == "BILIBILI"
        assert job.payload_json["text"] == ""
        assert job.status == "QUEUED"
