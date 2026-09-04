from __future__ import annotations

from dataclasses import dataclass, field

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
    typecode: str = ""
    coordinate_system: str = "GCJ02"
    score: int = 0
    match_reasons: list[str] = field(default_factory=list)


class AMapPOIProvider:
    endpoint = "https://restapi.amap.com/v5/place"

    def __init__(self, api_key: str, timeout: float = 20) -> None:
        self.api_key = api_key
        self.timeout = timeout

    def search(self, keywords: str, city: str = "", *, city_limit: bool = True) -> list[POICandidate]:
        return self._request(
            "text",
            {"keywords": keywords, "city": city, "citylimit": str(city_limit).lower(), "page_size": 20},
        )

    def around(self, longitude: float, latitude: float, keywords: str = "") -> list[POICandidate]:
        return self._request(
            "around",
            {"location": f"{longitude},{latitude}", "keywords": keywords, "radius": 1000, "page_size": 20},
        )

    def detail(self, poi_id: str) -> POICandidate | None:
        candidates = self._request("detail", {"id": poi_id})
        return candidates[0] if candidates else None

    def _request(self, operation: str, params: dict[str, object]) -> list[POICandidate]:
        if not self.api_key:
            raise RuntimeError("尚未配置高德 Web 服务 API Key")
        response = httpx.get(
            f"{self.endpoint}/{operation}", params={"key": self.api_key, **params}, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()
        if str(data.get("status")) != "1":
            raise RuntimeError(data.get("info") or "高德 POI 查询失败")
        return [candidate for poi in data.get("pois", []) if (candidate := self._candidate(poi))]

    @staticmethod
    def _candidate(poi: object) -> POICandidate | None:
        if not isinstance(poi, dict):
            return None
        try:
            longitude, latitude = (float(part) for part in str(poi["location"]).split(","))
        except (KeyError, ValueError):
            return None
        return POICandidate(
            provider_id=str(poi.get("id") or poi.get("poi_id") or ""),
            name=str(poi.get("name") or ""),
            address=poi.get("address") if isinstance(poi.get("address"), str) else "",
            province=str(poi.get("pname") or poi.get("province") or ""),
            city=str(poi.get("cityname") or poi.get("city") or ""),
            district=str(poi.get("adname") or poi.get("district") or ""),
            longitude=longitude,
            latitude=latitude,
            typecode=str(poi.get("typecode") or ""),
        )
