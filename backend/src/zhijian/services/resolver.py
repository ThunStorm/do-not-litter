from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

import httpx

from zhijian.services.documents import read_document


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.links: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._ignored_depth += 1
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth and data.strip():
            self.parts.append(data.strip())

    @property
    def text(self) -> str:
        return "\n".join(self.parts)


def resolve_payload(payload: dict) -> tuple[str, list[dict], dict]:
    supplied_text = str(payload.get("text") or "")
    if supplied_text.strip():
        segments = [
            {"text": block.strip(), "locator": {"paragraph": index + 1}}
            for index, block in enumerate(re.split(r"\n{2,}", supplied_text))
            if block.strip()
        ]
        return supplied_text, segments, {"resolver": "supplied_text"}

    file_path = payload.get("file_path")
    if file_path:
        text, segments = read_document(Path(file_path))
        return text, segments, {"resolver": "document", "file_path": file_path}

    locator = str(payload.get("locator") or "")
    if locator.startswith(("http://", "https://")):
        headers = {"User-Agent": "Mozilla/5.0 Zhijian/0.1 (+local-first personal reader)"}
        with httpx.Client(timeout=20, follow_redirects=True, headers=headers) as client:
            response = client.get(locator)
            response.raise_for_status()
        parser = TextExtractor()
        parser.feed(response.text)
        segments = [
            {"text": block, "locator": {"paragraph": index + 1}} for index, block in enumerate(parser.parts)
        ]
        return (
            parser.text,
            segments,
            {
                "resolver": "http",
                "status_code": response.status_code,
                "links": parser.links[:200],
                "content_type": response.headers.get("content-type", ""),
            },
        )

    raise ValueError("Capture 没有可解析的正文、文件或 URL")
