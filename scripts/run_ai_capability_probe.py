"""Probe configured Ollama text models and emit a stage capability matrix.

The tool is opt-in: it contacts Ollama only when an operator executes it.
"""
from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib import request

DEFAULT_MODELS = ("qwen2.5:7b", "qwen3:8b", "qwen3.5:9b")
PROBES = {
    "CLASSIFY": ("把文本分类为 travel，返回 JSON: {category: travel}。文本：故宫游览", "category", "travel"),
    "STRUCTURED_EXTRACT": ("提取 JSON: {items: [{name: 故宫}]}。文本：故宫上午开门", "items", "故宫"),
    "ENTITY_EXTRACT": ("提取 JSON: {entities: [故宫, 景山]}。文本：故宫和景山", "entities", "故宫"),
    "TRANSCRIPT_CORRECT": ("校对并返回 JSON: {changes: [{text: 西安蓝田水陆庵}]}。文本：闪西兰田水路案", "changes", "水陆庵"),
    "NOTE_GENERATE": ("生成 JSON: {note: 故宫上午开门}。文本：故宫上午开门", "note", "故宫"),
    "PLACE_EXTRACT": ("提取 JSON: {places: [故宫]}。文本：去故宫", "places", "故宫"),
    "PLACE_INSIGHT": ("提取 JSON: {insights: [{place: 故宫}]}。文本：故宫上午去", "insights", "故宫"),
    "PLACE_AGGREGATE": ("聚合 JSON: {places: [故宫]}。片段：故宫上午开门", "places", "故宫"),
    "POI_CONTEXT_RANK": ("排序 JSON: {candidates: [故宫]}。候选：故宫，景山", "candidates", "故宫"),
}


def request_json(base_url: str, model: str, prompt: str) -> dict[str, Any]:
    body = json.dumps(
        {"model": model, "stream": False, "format": "json", "messages": [{"role": "user", "content": prompt}]}
    ).encode()
    call = request.Request(f"{base_url.rstrip('/')}/api/chat", data=body, headers={"Content-Type": "application/json"})
    with request.urlopen(call, timeout=120) as response:  # nosec B310 - operator-supplied local Ollama endpoint
        payload = json.loads(response.read().decode())
    return json.loads(str(payload["message"]["content"]))


def probe_model(model: str, caller: Callable[[str, str], dict[str, Any]]) -> dict[str, str]:
    matrix: dict[str, str] = {}
    for stage, (prompt, required_field, expected_text) in PROBES.items():
        try:
            value = caller(model, prompt)
            response = value.get(required_field)
            matrix[stage] = "PASS" if response and expected_text in json.dumps(response, ensure_ascii=False) else "DEGRADED"
        except (KeyError, OSError, TypeError, ValueError):  # pragma: no cover - operator network behaviour
            matrix[stage] = "FAIL"
    matrix["VISION_FACT"] = "NOT_TESTED"
    return matrix


def main() -> None:
    parser = argparse.ArgumentParser(description="执行本地 Ollama Capability Probe")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--model", action="append", dest="models", help="可重复；默认三种已知本地文本模型")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    models = args.models or list(DEFAULT_MODELS)
    result = {
        "provider": "Ollama",
        "models": {model: probe_model(model, lambda name, prompt: request_json(args.base_url, name, prompt)) for model in models},
        "notice": "Probe 不会修改 Model Profile、Stage Policy 或默认路由。VISION_FACT 需要单独 image-capable Profile。",
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
