from __future__ import annotations

from zhijian.db.models import PlaceMention, Segment
from zhijian.providers.amap import POICandidate
from zhijian.services.evidence_trace import evidence_trace
from zhijian.services.video_support import (
    _poi_competitor,
    _poi_detail_consistent,
    _poi_review_reasons,
    _rank_poi_candidates,
)


def candidate(poi_id: str, name: str, city: str = "丽江市") -> POICandidate:
    return POICandidate(poi_id, name, "玉龙县", "云南省", city, "玉龙县", 100.25, 27.09, "110202")


def test_trace_accepts_only_exact_consecutive_same_snapshot() -> None:
    segments = [
        Segment(id="s1", snapshot_id="snap", ordinal=1, text="推荐玉龙", locator_json={}),
        Segment(id="s2", snapshot_id="snap", ordinal=2, text="雪山景区", locator_json={}),
        Segment(id="s4", snapshot_id="snap", ordinal=4, text="玉龙雪山", locator_json={}),
    ]
    assert evidence_trace(segments, ["s1", "s2"], "玉龙雪山", "snap")["valid"]
    assert not evidence_trace(segments, ["s1", "s4"], "玉龙玉龙", "snap")["valid"]
    assert not evidence_trace(segments, ["s2", "s1"], "景区推荐", "snap")["valid"]
    assert not evidence_trace(segments, ["s1", "s1"], "玉龙", "snap")["valid"]
    assert not evidence_trace(segments, ["s1", "s2"], "玉龙雪山区", "snap")["valid"]
    assert not evidence_trace(segments, ["s1", "s2"], "玉龙雪山", "other")["valid"]


def test_scenic_child_does_not_compete_but_geo_gate_remains() -> None:
    parent = candidate("parent", "玉龙雪山国家级风景名胜区")
    child = candidate("child", "玉龙雪山国家级风景名胜区-情人湖")

    class Provider:
        def search(self, *_args, **_kwargs):
            return [child, parent]

    mention = PlaceMention(
        id="m",
        name="玉龙雪山",
        raw_name="玉龙雪山",
        suggested_name="玉龙雪山",
        place_type="SCENIC_AREA",
        metadata_json={},
    )
    result = _rank_poi_candidates(Provider(), mention)
    assert [v.provider_id for v in result] == ["parent", "child"]
    assert _poi_competitor(result) is None
    reasons = _poi_review_reasons(result[0], _poi_competitor(result))
    assert "地域上下文不足" in reasons
    assert "第一、二候选差距过小" not in reasons
    result[1].city = "别的市"
    assert _poi_competitor(result) is result[1]


def test_partial_query_failure_preserves_candidates_but_forces_review() -> None:
    class Provider:
        def __init__(self):
            self.n = 0

        def search(self, *_args, **_kwargs):
            self.n += 1
            if self.n == 1:
                return [candidate("parent", "玉龙雪山国家级风景名胜区")]
            raise RuntimeError("HTTP 429")

    mention = PlaceMention(
        id="m",
        name="玉龙雪山",
        raw_name="玉龙雪山",
        suggested_name="玉龙雪山",
        city_hint="丽江市",
        place_type="SCENIC_AREA",
        metadata_json={},
    )
    result = _rank_poi_candidates(Provider(), mention)
    assert len(result) == 1
    assert result.trace["status"] == "PARTIAL"
    assert "查询结果不完整" in _poi_review_reasons(result[0], None)


def test_detail_requires_same_poi_and_consistent_coordinates() -> None:
    original = candidate("parent", "玉龙雪山国家级风景名胜区")
    assert _poi_detail_consistent(original, candidate("parent", original.name))
    assert not _poi_detail_consistent(original, candidate("other", original.name))
    assert not _poi_detail_consistent(original, candidate("parent", original.name, "大理市"))
    moved = candidate("parent", original.name)
    moved.longitude += 1
    assert not _poi_detail_consistent(original, moved)


def test_area_government_requires_exact_scope_and_detail() -> None:
    from dataclasses import replace

    from zhijian.services.area_anchors import government_anchor

    seat = POICandidate(
        "government",
        "昆明市人民政府",
        "昆明市",
        "云南省",
        "昆明市",
        "呈贡区",
        102.83,
        24.88,
        "130100",
        adcode="530100",
    )

    class Provider:
        def __init__(self, candidates, detail):
            self.candidates, self.detail_value = candidates, detail

        def search(self, *_args, **_kwargs):
            return self.candidates

        def detail(self, _id):
            return self.detail_value

    args = {"area": "昆明市", "province": "云南省", "city": "昆明市", "district": ""}
    anchor = government_anchor(Provider([seat], seat), **args)
    assert anchor and anchor["kind"] == "GOVERNMENT_SEAT"
    assert government_anchor(Provider([replace(seat, name="昆明市政务服务中心")], seat), **args) is None
    assert government_anchor(Provider([seat, replace(seat, provider_id="other")], seat), **args) is None
    assert government_anchor(Provider([seat], replace(seat, provider_id="other")), **args) is None
    assert government_anchor(Provider([seat], seat), **{**args, "province": ""}) is None
    assert (
        government_anchor(
            Provider([seat], seat), **{**args, "area": "西山区", "district": "西山区", "city": ""}
        )
        is None
    )


def test_area_map_preserves_destination_identity_and_no_other_area_merge(client, app_and_session) -> None:
    from sqlalchemy import select

    from zhijian.db.models import Destination, Place, Snapshot, Source, VideoAsset
    from zhijian.services.video_support import materialize_destinations

    _, factory = app_and_session
    seat = POICandidate(
        "government",
        "昆明市人民政府",
        "昆明市",
        "云南省",
        "昆明市",
        "呈贡区",
        102.83,
        24.88,
        "130100",
        adcode="530100",
    )

    class Provider:
        def search(self, *_args, **_kwargs):
            return [seat]

        def detail(self, _id):
            return seat

    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/area")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator)
        db.add(asset)
        db.flush()
        snapshot = Snapshot(
            source_id=source.id, content_hash="area", metadata_json={"video_asset_id": asset.id}
        )
        db.add(snapshot)
        db.flush()
        segment = Segment(snapshot_id=snapshot.id, ordinal=0, text="推荐昆明市", locator_json={})
        db.add(segment)
        db.flush()
        mention = PlaceMention(
            video_asset_id=asset.id,
            name="昆明市",
            raw_name="昆明市",
            suggested_name="昆明市",
            city_hint="昆明市",
            province_hint="云南省",
            poi_policy="AREA_RESOLVE",
            subject_role="PRIMARY",
            visit_intent="RECOMMENDED",
            segment_ids_json=[segment.id],
            quote="推荐昆明市",
            extraction_status="EXTRACTED",
            content_unit_id="area-unit",
            metadata_json={},
        )
        db.add(mention)
        db.flush()
        materialize_destinations(db, asset, [mention], Provider())
        destination_id = mention.destination_id
        assert destination_id and mention.place_id is None
        assert mention.metadata_json["representative_anchor"]["provider_id"] == "government"
        assert db.scalar(select(Place).where(Place.external_poi_id == "government")) is None
        db.add(
            Destination(
                name="昆明市",
                canonical_name="昆明市",
                scope_type="CITY",
                province="其他省",
                city="昆明市",
                district="",
            )
        )
        db.commit()
    data = client.get("/api/travel/map").json()
    marker = next(item for item in data["markers"] if item["id"] == destination_id)
    assert marker["entity_type"] == "DESTINATION"
    assert marker["place_id"] is None
    assert marker["name"] == "昆明市"
    assert marker["address"] == "昆明市人民政府"
    assert client.get("/api/travel/map", params={"query": "不匹配"}).json()["markers"] == []
    assert any(
        item["id"] == destination_id
        for item in client.get("/api/travel/map", params={"place_type": "AREA"}).json()["markers"]
    )
    assert not any(
        item["id"] == destination_id
        for item in client.get("/api/travel/map", params={"place_type": "MUSEUM"}).json()["markers"]
    )
    from zhijian.db.models import PlaceDeletionTombstone

    with factory() as db:
        db.add(
            PlaceDeletionTombstone(
                external_provider="AMAP", external_poi_id="government", former_place_id="deleted"
            )
        )
        db.commit()
    assert not any(item["id"] == destination_id for item in client.get("/api/travel/map").json()["markers"])


def test_scenic_entry_is_separate_destination_and_multiple_entries_require_review(
    client, app_and_session, monkeypatch
) -> None:
    from dataclasses import replace

    from sqlalchemy import select

    from zhijian.core.config import Settings
    from zhijian.db.models import Destination, Place, Snapshot, Source, VideoAsset
    from zhijian.services.video_support import resolve_mentions_with_amap

    center = candidate("center", "玉龙雪山国家级风景名胜区-游客接待中心")

    class Provider:
        def __init__(self, *_args, **_kwargs):
            self.request_count = self.cache_hit_count = 0

        def search(self, *_args, **_kwargs):
            return [center]

        def detail(self, _poi_id):
            return center

    monkeypatch.setattr("zhijian.services.video_support.AMapPOIProvider", Provider)
    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/scenic")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator)
        db.add(asset)
        db.flush()
        snapshot = Snapshot(
            source_id=source.id, content_hash="scenic", metadata_json={"video_asset_id": asset.id}
        )
        db.add(snapshot)
        db.flush()
        segment = Segment(snapshot_id=snapshot.id, ordinal=0, text="推荐玉龙雪山", locator_json={})
        db.add(segment)
        db.flush()
        mention = PlaceMention(
            video_asset_id=asset.id,
            name="玉龙雪山",
            raw_name="玉龙雪山",
            suggested_name="玉龙雪山",
            city_hint="丽江市",
            province_hint="云南省",
            place_type="SCENIC_AREA",
            poi_policy="RESOLVE",
            subject_role="PRIMARY",
            visit_intent="RECOMMENDED",
            segment_ids_json=[segment.id],
            quote="推荐玉龙雪山",
            extraction_status="EXTRACTED",
            metadata_json={},
        )
        db.add(mention)
        db.commit()
        metrics = {}
        assert resolve_mentions_with_amap(db, Settings(_env_file=None), [mention], "fixture", metrics) == (
            0,
            0,
        )
        assert metrics["poi_scenic_anchor"] == 1
        assert mention.place_id is None and mention.resolution_status == "AREA_RESOLVED"
        destination = db.get(Destination, mention.destination_id)
        assert destination and destination.name == "玉龙雪山"
        assert db.scalar(select(Place).where(Place.external_poi_id == "center")) is None
        destination_id = destination.id

        class TwoCenters(Provider):
            def search(self, *_args, **_kwargs):
                return [
                    center,
                    replace(center, provider_id="second", name="玉龙雪山国家级风景名胜区-游客中心"),
                ]

        monkeypatch.setattr("zhijian.services.video_support.AMapPOIProvider", TwoCenters)
        another = PlaceMention(
            video_asset_id=asset.id,
            name="玉龙雪山",
            raw_name="玉龙雪山",
            suggested_name="玉龙雪山",
            city_hint="丽江市",
            province_hint="云南省",
            place_type="SCENIC_AREA",
            poi_policy="RESOLVE",
            subject_role="PRIMARY",
            visit_intent="RECOMMENDED",
            segment_ids_json=[segment.id],
            quote="推荐玉龙雪山",
            extraction_status="EXTRACTED",
            metadata_json={},
        )
        db.add(another)
        db.commit()
        assert resolve_mentions_with_amap(db, Settings(_env_file=None), [another], "fixture") == (0, 1)
        assert another.resolution_status == "REVIEW" and another.destination_id is None
    data = client.get("/api/travel/map").json()
    marker = next(item for item in data["markers"] if item["id"] == destination_id)
    assert marker["entity_type"] == "DESTINATION" and marker["place_id"] is None
    assert marker["brief"]["anchor_kind"] == "SCENIC_ENTRY"


def test_manual_search_uses_ranking_preserves_revision_and_reports_failure(
    client, app_and_session, monkeypatch
) -> None:
    from types import SimpleNamespace

    from zhijian.api.router import get_secret_store
    from zhijian.db.models import Source, VideoAsset

    class Provider:
        def __init__(self, _key):
            self.refresh_empty = False

        def search(self, *_args, **_kwargs):
            return [candidate("parent", "玉龙雪山国家级风景名胜区")]

    monkeypatch.setattr("zhijian.api.router.AMapPOIProvider", Provider)
    app, factory = app_and_session
    app.dependency_overrides[get_secret_store] = lambda: SimpleNamespace(get=lambda _key: "fixture")
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/manual-search")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator)
        db.add(asset)
        db.flush()
        mention = PlaceMention(
            video_asset_id=asset.id,
            name="玉龙雪山",
            raw_name="玉龙雪山",
            suggested_name="玉龙雪山",
            city_hint="丽江市",
            place_type="SCENIC_AREA",
            poi_policy="RESOLVE",
            resolution_status="REVIEW",
            metadata_json={},
        )
        db.add(mention)
        db.commit()
        mention_id = mention.id
    url = f"/api/travel/place-mentions/{mention_id}/poi-search"
    response = client.post(url, json={"query": "玉龙雪山", "expected_revision": 0})
    assert response.status_code == 200
    assert response.json()["revision"] == 1
    assert response.json()["candidates"][0]["score"] > 0
    assert client.post(url, json={"query": "玉龙雪山", "expected_revision": 0}).status_code == 409

    class FailingProvider(Provider):
        def search(self, *_args, **_kwargs):
            raise RuntimeError("HTTP 429")

    monkeypatch.setattr("zhijian.api.router.AMapPOIProvider", FailingProvider)
    assert client.post(url, json={"query": "玉龙雪山", "expected_revision": 1}).status_code == 502
    with factory() as db:
        mention = db.get(PlaceMention, mention_id)
        assert mention.revision == 1
        assert mention.metadata_json["manual_search_trace"]["mode"] == "MANUAL"


def test_search_falls_back_after_empty_but_stops_for_unambiguous_scoped_exact() -> None:
    mention = PlaceMention(
        id="m",
        name="玉龙雪山",
        raw_name="玉龙雪山",
        suggested_name="玉龙雪山",
        city_hint="丽江市",
        province_hint="云南省",
        place_type="SCENIC_AREA",
        metadata_json={},
    )

    class ExactProvider:
        def __init__(self):
            self.calls = []

        def search(self, query, city, **_kwargs):
            self.calls.append((query, city))
            return [candidate("exact", "玉龙雪山")]

    exact = ExactProvider()
    result = _rank_poi_candidates(exact, mention)
    assert len(exact.calls) == 1
    assert result.trace["fallback_skipped"] == "SCOPED_EXACT"

    class EmptyFirst(ExactProvider):
        def search(self, query, city, **kwargs):
            self.calls.append((query, city))
            return [] if len(self.calls) == 1 else [candidate("exact", "玉龙雪山")]

    fallback = EmptyFirst()
    result = _rank_poi_candidates(fallback, mention)
    assert len(fallback.calls) > 1
    assert result.trace["queries"][0]["status"] == "EMPTY"
    assert result[0].provider_id == "exact"
    assert "QUERY_DISAGREEMENT" not in result[0].match_explanation["negative_evidence"]
