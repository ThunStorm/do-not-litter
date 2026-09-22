from __future__ import annotations

import json
from concurrent.futures import Future
from dataclasses import dataclass, field, replace
from threading import Lock
from time import monotonic
from typing import ClassVar

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
    match_explanation: dict[str, object] = field(default_factory=dict)


class AMapPOIProvider:
    endpoint = "https://restapi.amap.com/v5/place"
    _cache: ClassVar[dict[str, tuple[float, list[POICandidate]]]] = {}
    _inflight: ClassVar[dict[str, Future[list[POICandidate]]]] = {}
    _lock: ClassVar[Lock] = Lock()

    def __init__(self, api_key: str, timeout: float = 20, *, cache_ttl_seconds: int = 86400) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self.cache_ttl_seconds = cache_ttl_seconds
        self.request_count = 0
        self.cache_hit_count = 0

    def search(self, keywords: str, city: str = "", *, city_limit: bool = True) -> list[POICandidate]:
        return self._request(
            "text",
            {"keywords": keywords, "city": city, "citylimit": str(city_limit).lower(), "page_size": 20},
        )

    def around(
        self, longitude: float, latitude: float, keywords: str = "", *, radius: int = 1000
    ) -> list[POICandidate]:
        return self._request(
            "around",
            {
                "location": f"{longitude},{latitude}",
                "keywords": keywords,
                "radius": max(100, min(radius, 5000)),
                "page_size": 20,
            },
        )

    def detail(self, poi_id: str) -> POICandidate | None:
        candidates = self._request("detail", {"id": poi_id})
        return candidates[0] if candidates else None

    def _request(self, operation: str, params: dict[str, object]) -> list[POICandidate]:
        if not self.api_key:
            raise RuntimeError("尚未配置高德 Web 服务 API Key")
        key = f"{self.endpoint}/{operation}:" + json.dumps(params, ensure_ascii=False, sort_keys=True)
        now = monotonic()
        with self._lock:
            cached = self._cache.get(key)
            if cached and now - cached[0] <= self.cache_ttl_seconds:
                self.cache_hit_count += 1
                return self._clones(cached[1])
            future = self._inflight.get(key)
            owner = future is None
            if owner:
                future = self._inflight[key] = Future()
        if not owner:
            self.cache_hit_count += 1
            return self._clones(future.result(timeout=self.timeout + 5))
        try:
            self.request_count += 1
            response = httpx.get(
                f"{self.endpoint}/{operation}",
                params={"key": self.api_key, **params},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            if str(data.get("status")) != "1":
                raise RuntimeError(data.get("info") or "高德 POI 查询失败")
            values = [candidate for poi in data.get("pois", []) if (candidate := self._candidate(poi))]
            with self._lock:
                self._cache[key] = (monotonic(), values)
            future.set_result(values)
            return self._clones(values)
        except Exception as exc:
            future.set_exception(exc)
            raise
        finally:
            with self._lock:
                self._inflight.pop(key, None)

    @staticmethod
    def _clones(values: list[POICandidate]) -> list[POICandidate]:
        return [
            replace(
                value,
                match_reasons=list(value.match_reasons),
                match_explanation=dict(value.match_explanation),
            )
            for value in values
        ]

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
