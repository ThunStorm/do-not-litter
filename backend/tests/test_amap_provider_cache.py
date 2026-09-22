from zhijian.providers.amap import AMapPOIProvider


def test_amap_provider_coalesces_duplicate_query_without_sharing_mutation(monkeypatch) -> None:
    calls = 0

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "status": "1",
                "pois": [{"id": "poi-1", "name": "大理古城", "location": "100,20"}],
            }

    def get(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return Response()

    AMapPOIProvider._cache.clear()
    monkeypatch.setattr("zhijian.providers.amap.httpx.get", get)
    provider = AMapPOIProvider("fixture")
    first = provider.search("大理古城", "大理")
    first[0].score = 99
    second = provider.search("大理古城", "大理")

    assert calls == provider.request_count == 1
    assert provider.cache_hit_count == 1
    assert second[0].score == 0
