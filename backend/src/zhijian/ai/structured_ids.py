"""Conservative, response-local ID recovery; never infer semantic references."""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any

from zhijian.ai.reliability import AIProviderError

ID_REPAIR_VERSION = "ground-map-claim-ids-v1"
SAFE_FIELDS = {
    "content_units",
    "entities",
    "claims",
    "relations",
    "warnings",
    "content_unit_id",
    "entity_id",
    "claim_id",
    "claim_ids",
    "unit_id",
    "anchor_entity_ids",
    "source_entity_id",
    "target_entity_id",
    "subject_entity_ids",
    "segment_id",
    "segment_ids",
    "target_ids",
    "mention_id",
    "place_mention_ids",
    "changes",
}
ISSUE_MESSAGES = {
    "MISSING_LOCAL_ID": "局部事实 ID 缺省",
    "DUPLICATE_LOCAL_ID": "局部事实 ID 重复",
    "INVALID_LOCAL_ID": "局部事实 ID 必须为非空字符串",
    "INVALID_LOCAL_ITEM": "局部事实条目必须为对象",
    "CLAIM_REFERENCE_UNSAFE": "Claim ID 存在反向引用，不能安全重编号",
    "UNKNOWN_LOCAL_REFERENCE": "事实关系指向不存在的实体或单元",
    "UNKNOWN_EVIDENCE_ID": "模型引用未知或越界 Evidence ID",
}


def child_path(path: str, key: str | int) -> str:
    return f"{path}[{key}]" if isinstance(key, int) else f"{path}.{key if key in SAFE_FIELDS else '*'}"


def schema_issue(
    kind: str, path: str, *, related_path: str | None = None, identifier: Any = None
) -> AIProviderError:
    diagnostic = {"kind": kind, "path": path[:160]}
    if related_path:
        diagnostic["related_path"] = related_path[:160]
    if identifier is not None:
        diagnostic["id_sha256"] = sha256(str(identifier).encode()).hexdigest()
    error = AIProviderError("AI_PROVIDER_SCHEMA_INVALID", f"{ISSUE_MESSAGES[kind]}（{diagnostic['path']}）")
    error.schema_diagnostic = diagnostic
    return error


def repair_claim_ids(payload: dict[str, Any], scope: str) -> list[dict[str, Any]]:
    """Repair only unreferenced, missing/duplicate claim labels, keeping every record."""
    claims = payload.get("claims", [])
    if not isinstance(claims, list):
        return []  # The ordinary schema validator owns collection types.
    seen: set[str] = set()
    pending: list[tuple[int, str, Any]] = []
    for index, item in enumerate(claims):
        path = f"$.claims[{index}].claim_id"
        if not isinstance(item, dict):
            raise schema_issue("INVALID_LOCAL_ITEM", f"$.claims[{index}]")
        identifier = item.get("claim_id")
        if identifier is None or isinstance(identifier, str) and not identifier.strip():
            pending.append((index, "MISSING_LOCAL_ID", identifier))
        elif not isinstance(identifier, str):
            raise schema_issue("INVALID_LOCAL_ID", path)
        elif identifier in seen:
            pending.append((index, "DUPLICATE_LOCAL_ID", identifier))
        else:
            seen.add(identifier)
    if not pending:
        return []

    def reference_path(value: Any, path: str = "$") -> str | None:
        if isinstance(value, dict):
            for key, item in value.items():
                definition = key == "claim_id" and path.startswith("$.claims[") and path.count(".") == 1
                if item and not definition and (key.endswith("claim_id") or key.endswith("claim_ids")):
                    return child_path(path, key)
                found = reference_path(item, child_path(path, key))
                if found:
                    return found
        elif isinstance(value, list):
            for index, item in enumerate(value):
                found = reference_path(item, child_path(path, index))
                if found:
                    return found
        return None

    reference = reference_path(payload)
    if reference:
        raise schema_issue(
            "CLAIM_REFERENCE_UNSAFE", f"$.claims[{pending[0][0]}].claim_id", related_path=reference
        )
    repairs = []
    for index, reason, original in pending:
        item = claims[index]
        seed = [scope, index, {key: value for key, value in item.items() if key != "claim_id"}]
        digest = sha256(json.dumps(seed, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        identifier = f"local_claim_{digest}"
        while identifier in seen:
            identifier += "_"
        seen.add(identifier)
        item["claim_id"] = identifier
        repair = {"path": f"$.claims[{index}].claim_id", "reason": reason, "new_id": identifier}
        if original is not None:
            repair["original_id_sha256"] = sha256(str(original).encode()).hexdigest()
        repairs.append(repair)
    return repairs
