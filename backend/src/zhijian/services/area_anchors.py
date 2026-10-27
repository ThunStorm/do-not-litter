"""Conservative representative anchors; the POI is not the destination identity."""

from __future__ import annotations

import json
import math
import re
from hashlib import sha256
from typing import TYPE_CHECKING, Any

from zhijian.providers.amap import POICandidate

if TYPE_CHECKING:
    from zhijian.db.models import Destination, PlaceMention


def _anchor_binding(
    destination: Destination, mention: PlaceMention, source_id: str, snapshot_id: str
) -> dict:
    opinion = (mention.metadata_json or {}).get("recommendation_evidence")
    context = (mention.metadata_json or {}).get("resolver_context", {})
    context = context if isinstance(context, dict) else {}
    return {
        "version": "poi-anchor-binding-v1",
        "destination_id": destination.id,
        "destination_identity": [
            destination.scope_type,
            destination.canonical_name,
            destination.province,
            destination.city,
            destination.district,
        ],
        "video_asset_id": mention.video_asset_id,
        "source_id": source_id,
        "snapshot_id": snapshot_id,
        "segment_ids": list(mention.segment_ids_json),
        "quote_sha256": sha256(mention.quote.encode()).hexdigest(),
        "target": [
            mention.name,
            mention.raw_name,
            mention.suggested_name,
            mention.city_hint,
            mention.province_hint,
            mention.poi_policy,
            mention.subject_role,
            mention.visit_intent,
        ],
        "opinion_sha256": sha256(
            json.dumps(opinion, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest(),
        "region_context": [
            context.get(key)
            for key in ("unit_city", "geo_session_city", "geo_session_province", "district_hint")
        ],
    }


def bind_representative_anchor(
    anchor: dict, destination: Destination, mention: PlaceMention, source_id: str, snapshot_id: str
) -> dict:
    return {
        **anchor,
        "snapshot_id": snapshot_id,
        "segment_ids": list(mention.segment_ids_json),
        "binding": _anchor_binding(destination, mention, source_id, snapshot_id),
    }


def representative_anchor_valid(
    anchor: object, destination: Destination, mention: PlaceMention, source_id: str
) -> bool:
    if not isinstance(anchor, dict) or anchor.get("kind") not in {"GOVERNMENT_SEAT", "SCENIC_ENTRY"}:
        return False
    if (
        not source_id
        or not anchor.get("snapshot_id")
        or not anchor.get("provider_id")
        or not anchor.get("name")
    ):
        return False
    if anchor.get("coordinate_system") != "GCJ02":
        return False
    longitude, latitude = anchor.get("longitude"), anchor.get("latitude")
    if not all(
        isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)
        for value in (longitude, latitude)
    ):
        return False
    if not (73.5 <= longitude <= 135.1 and 18 <= latitude <= 53.6):
        return False
    if anchor["kind"] == "GOVERNMENT_SEAT" and destination.scope_type not in {"CITY", "DISTRICT"}:
        return False
    if anchor["kind"] == "SCENIC_ENTRY" and destination.scope_type != "SCENIC_AREA":
        return False
    return anchor.get("binding") == _anchor_binding(destination, mention, source_id, anchor["snapshot_id"])


def government_anchor(
    provider: Any, *, area: str, province: str, city: str, district: str
) -> dict[str, Any] | None:
    area, province, city, district = (item.strip() for item in (area, province, city, district))
    is_city = area.endswith(("市", "自治州"))
    is_district = area.endswith(("县", "区", "自治县"))
    if not province or not (is_city or is_district) or (is_district and (not city or district != area)):
        return None
    if is_city and city != area:
        return None
    expected = f"{area}人民政府"

    def matches(item: POICandidate) -> bool:
        return bool(
            item.name == expected
            and item.provider_id
            and item.province == province
            and item.city == city
            and (not is_district or item.district == district)
            and item.typecode.startswith("13")
            and re.fullmatch(r"\d{6}", item.adcode)
            and 73.5 <= item.longitude <= 135.1
            and 18 <= item.latitude <= 53.6
        )

    try:
        values = provider.search(expected, city, city_limit=True)
        if len(values) >= 20:
            return None
        candidates = [item for item in values if matches(item)]
        if len({item.provider_id for item in candidates}) != 1:
            return None
        selected = candidates[0]
        detail = provider.detail(selected.provider_id)
    except Exception:
        return None
    if not detail or not matches(detail) or detail.provider_id != selected.provider_id:
        return None
    if detail.adcode != selected.adcode or abs(detail.latitude - selected.latitude) > 0.003:
        return None
    if abs(detail.longitude - selected.longitude) > 0.003:
        return None
    return {
        "kind": "GOVERNMENT_SEAT",
        "provider": "AMAP",
        "provider_id": detail.provider_id,
        "name": detail.name,
        "province": province,
        "city": city,
        "district": district,
        "adcode": detail.adcode,
        "latitude": detail.latitude,
        "longitude": detail.longitude,
        "coordinate_system": "GCJ02",
        "version": "area-anchor-v1",
    }
