"""Lossless request-boundary projections. Canonical artifacts never use short IDs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from zhijian.ai.reliability import AIProviderError
from zhijian.ai.structured_output import parse_json_object
from zhijian.db.models import Segment

COMPILER_VERSION = "stage-evidence-v1"
SEGMENT_FIELDS = {"segment_id", "segment_ids", "target_ids"}
MENTION_FIELDS = {"mention_id", "place_mention_ids"}


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return sha256(compact(value).encode()).hexdigest()


@dataclass
class CompiledRequest:
    messages: list[dict[str, str]]
    identity: dict[str, str]
    ids: dict[str, str]
    allowed: set[str]
    stage: str
    targets: set[str] | None = None

    def decode(self, content: str, *, namespace_ids: bool = True) -> str:
        reverse = {value: key for key, value in self.ids.items()}

        def restore(value: Any, key: str = "") -> Any:
            if isinstance(value, dict):
                return {field: restore(item, field) for field, item in value.items()}
            if isinstance(value, list):
                return [restore(item, key) for item in value]
            if key in SEGMENT_FIELDS | MENTION_FIELDS and isinstance(value, str):
                canonical = reverse.get(value, value)
                if canonical not in self.allowed:
                    raise AIProviderError("AI_PROVIDER_SCHEMA_INVALID", "模型引用未知或越界 Evidence ID")
                return canonical
            return value

        payload = restore(parse_json_object(content))
        if self.targets is not None:
            changes = payload.get("changes")
            identifiers = (
                [item.get("segment_id") for item in changes if isinstance(item, dict)]
                if isinstance(changes, list)
                else []
            )
            if (
                not isinstance(changes, list)
                or len(identifiers) != len(changes)
                or len(identifiers) != len(set(identifiers))
                or any(item not in self.targets for item in identifiers)
            ):
                raise AIProviderError("AI_PROVIDER_SCHEMA_INVALID", "校对输出包含重复或只读上下文 ID")
        if namespace_ids and self.stage == "GROUND_MAP" and "entities" in payload:
            # Namespace model-created IDs by stable source interval, never chunk number/split path.
            scope = fingerprint([self.identity, sorted(self.allowed)])[:12]
            definitions = {"content_unit_id": "content_units", "entity_id": "entities", "claim_id": "claims"}
            local: dict[str, str] = {}
            for field, collection in definitions.items():
                seen: set[str] = set()
                for item in payload.get(collection, []):
                    identifier = str(item.get(field) or "") if isinstance(item, dict) else ""
                    if not identifier or identifier in seen:
                        raise AIProviderError("AI_PROVIDER_SCHEMA_INVALID", "局部事实 ID 缺省或重复")
                    seen.add(identifier)
                    local[f"{field}:{identifier}"] = f"{scope}:{fingerprint([field, identifier])[:16]}"

            references = {
                "unit_id": "content_unit_id",
                "anchor_entity_ids": "entity_id",
                "source_entity_id": "entity_id",
                "target_entity_id": "entity_id",
                "subject_entity_ids": "entity_id",
            }

            def namespace(value: Any, key: str = "") -> Any:
                if isinstance(value, dict):
                    return {field: namespace(item, field) for field, item in value.items()}
                if isinstance(value, list):
                    return [namespace(item, key) for item in value]
                field = references.get(key, key)
                if field in definitions and isinstance(value, str) and value:
                    if f"{field}:{value}" not in local:
                        raise AIProviderError("AI_PROVIDER_SCHEMA_INVALID", "事实关系指向不存在的实体或单元")
                    return local[f"{field}:{value}"]
                return value

            payload = namespace(payload)
        return compact(payload)


def compile_request(
    stage: str, messages: list[dict[str, str]], segments: list[Segment], snapshot_identity: str
) -> CompiledRequest:
    ordered = sorted(segments, key=lambda item: (item.ordinal, item.id))
    if len({item.id for item in ordered}) != len(ordered):
        raise ValueError("duplicate canonical Segment ID")
    if any(item.snapshot_id != snapshot_identity for item in ordered):
        raise ValueError("Segment belongs to another transcript")
    ids = {item.id: f"s{index}" for index, item in enumerate(ordered, 1)}
    texts = {
        item.id: (item.raw_text or item.text)
        if stage == "TRANSCRIPT_CORRECTION"
        else (item.corrected_text or item.text)
        for item in ordered
    }
    allowed: set[str] = set()
    targets_scope: set[str] | None = None

    def project(value: Any, key: str = "") -> Any:
        if isinstance(value, dict):
            return {field: project(item, field) for field, item in value.items()}
        if isinstance(value, list):
            return [project(item, key) for item in value]
        if key in SEGMENT_FIELDS | MENTION_FIELDS and isinstance(value, str):
            if key == "mention_id" and value not in ids:
                ids[value] = "p" + fingerprint(value)[:12]
            if value not in ids:
                raise ValueError("request contains out-of-snapshot Segment")
            allowed.add(value)
            return ids[value]
        return value

    rendered = []
    for message in messages:
        body = message["content"]
        if message["role"] != "user":
            rendered.append(dict(message))
            continue
        if stage == "TRANSCRIPT_CORRECTION":
            payload = json.loads(body)
            if "items" in payload:
                unique: dict[str, dict] = {}
                targets = []
                for item in payload.pop("items"):
                    target = item["target"]
                    targets.append(target["id"])
                    for entry in [*item.get("context_before", []), target, *item.get("context_after", [])]:
                        unique[entry["id"]] = {
                            "segment_id": entry["id"],
                            **{k: v for k, v in entry.items() if k != "id"},
                        }
                payload.update(segments=list(unique.values()), target_ids=list(dict.fromkeys(targets)))
            targets_scope = set(payload["target_ids"])
            body = compact(project(payload))
        else:
            # Only generated wrappers change. Raw text/quotes containing IDs or JSON stay untouched.
            cursor = 0
            pieces = []
            by_id = {item.id: item for item in ordered}
            pattern = re.compile(r"(?m)^\[segment:([^\s]+) ([^\]]+)\] ")
            while match := pattern.search(body, cursor):
                identifier = match[1]
                if identifier not in ids:
                    raise ValueError("transcript wrapper contains unknown Segment")
                source_text = by_id[identifier].corrected_text or by_id[identifier].text
                end = match.end() + len(source_text)
                if body[match.end() : end] != source_text:
                    raise ValueError("transcript wrapper does not match canonical evidence")
                allowed.add(identifier)
                pieces.extend(
                    [body[cursor : match.start()], f"[segment:{ids[identifier]} {match[2]}] ", source_text]
                )
                cursor = end
            body = "".join([*pieces, body[cursor:]])
            marker = "Evidence Index："
            if stage in {"GENERATE_AI_NOTE", "NOTE_REDUCE"} and marker in body:
                offset = body.index(marker) + len(marker)
                value, size = json.JSONDecoder().raw_decode(body[offset:])
                if stage == "NOTE_REDUCE":
                    pack_offset = body.index("仅据此生成全局笔记：\n") + len("仅据此生成全局笔记：\n")
                    pack = json.loads(body[pack_offset:])
                    quotes = {str(quote) for fact in pack for quote in fact.get("supporting_quotes", [])}
                    value = [
                        {
                            key: item
                            for key, item in entry.items()
                            if key != "quotes"
                            or not all(quote in quotes for quote in entry.get("quotes", []))
                        }
                        for entry in value
                    ]
                body = body[:offset] + compact(project(value)) + body[offset + size :]
            if stage == "NOTE_REDUCE":
                offset = body.index("仅据此生成全局笔记：\n") + len("仅据此生成全局笔记：\n")
                body = body[:offset] + compact(project(json.loads(body[offset:])))
        rendered.append({**message, "content": body})
    if stage == "TRANSCRIPT_CORRECTION":
        rendered[0] = {
            **rendered[0],
            "content": rendered[0]["content"]
            + "\n本次输入为去重 segments 和 target_ids；仅校对 target_ids，其他段只读。",
        }
    identity = {
        "compiler_version": COMPILER_VERSION,
        "stage_projection_version": f"{stage}-v1",
        "snapshot_identity": snapshot_identity,
        "source_content_hash": fingerprint([[item.id, texts[item.id]] for item in ordered]),
        "short_id_map_fingerprint": fingerprint(ids),
    }
    return CompiledRequest(rendered, identity, ids, allowed, stage, targets_scope)
