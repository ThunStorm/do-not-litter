from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass(slots=True)
class POICandidate:
    provider_id: str
    name: str
    address: str
    province: str
    city: str
    district: str
    longitude: float
    latitude: float
    coordinate_system: str = "GCJ02"


class AMapPOIProvider:
    endpoint = "https://restapi.amap.com/v3/place/text"

    def __init__(self, api_key: str, timeout: float = 20) -> None:
        self.api_key = api_key
        self.timeout = timeout

    def search(self, keywords: str, city: str, *, city_limit: bool = True) -> list[POICandidate]:
        if not self.api_key:
            raise RuntimeError("尚未配置高德 Web 服务 API Key")
        response = httpx.get(
            self.endpoint,
            params={
                "key": self.api_key,
                "keywords": keywords,
                "city": city,
                "citylimit": "true" if city_limit else "false",
                "offset": 10,
                "page": 1,
                "extensions": "base",
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "1":
            raise RuntimeError(data.get("info") or "高德 POI 查询失败")
        candidates = []
        for poi in data.get("pois", []):
            try:
                longitude, latitude = (float(part) for part in poi["location"].split(","))
            except (KeyError, TypeError, ValueError):
                continue
            candidates.append(
                POICandidate(
                    provider_id=poi.get("id", ""),
                    name=poi.get("name", ""),
                    address=poi.get("address") if isinstance(poi.get("address"), str) else "",
                    province=poi.get("pname", ""),
                    city=poi.get("cityname", ""),
                    district=poi.get("adname", ""),
                    longitude=longitude,
                    latitude=latitude,
                )
            )
        return candidates
