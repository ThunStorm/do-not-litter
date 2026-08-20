from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

_BVID = re.compile(r"(?:^|/)video/(BV[0-9A-Za-z]+)", re.I)


@dataclass(frozen=True, slots=True)
class BilibiliURL:
    bvid: str | None
    page_number: int
    is_short: bool


def parse_bilibili_url(url: str) -> BilibiliURL:
    parsed = urlparse(url)
    host = parsed.hostname.lower() if parsed.hostname else ""
    if host not in {"www.bilibili.com", "m.bilibili.com", "bilibili.com", "b23.tv", "www.b23.tv"}:
        raise ValueError("仅允许 Bilibili 视频链接")
    if parsed.scheme != "https":
        raise ValueError("视频链接必须使用 HTTPS")
    page_value = parse_qs(parsed.query).get("p", ["1"])[0]
    try:
        page_number = max(1, int(page_value))
    except ValueError:
        page_number = 1
    match = _BVID.search(parsed.path)
    return BilibiliURL(
        bvid=match.group(1) if match else None, page_number=page_number, is_short=host.endswith("b23.tv")
    )
