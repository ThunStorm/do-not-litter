"""Conservative representative anchors; the POI is not the destination identity."""

from __future__ import annotations

import re
from typing import Any

from zhijian.providers.amap import POICandidate


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
        candidates = [item for item in provider.search(expected, city, city_limit=True) if matches(item)]
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
