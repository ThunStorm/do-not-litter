from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

from sqlalchemy import select

from zhijian.core.config import Settings
from zhijian.db.models import PlaceMention, Source, VideoAsset
from zhijian.providers.amap import POICandidate
from zhijian.services.video_support import _poi_detail_consistent, resolve_mentions_with_amap


def poi() -> POICandidate:
    return POICandidate("p", "翠湖公园", "昆明市五华区", "云南省", "昆明市", "五华区", 102.7, 25.03, "110000")


def test_detail_cannot_drop_verified_fields():
    value = poi()
    for field in ("city", "province", "district", "typecode"):
        assert not _poi_detail_consistent(value, replace(value, **{field: ""})), field


def test_manual_negative_confirmation_survives_resolution(app_and_session):
    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/manual-opinion")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator)
        db.add(asset)
        db.flush()
        mention = PlaceMention(
            video_asset_id=asset.id,
            name="翠湖",
            visit_intent="NOT_RECOMMENDED",
            poi_policy="RESOLVE",
            resolution_status="CONFIRMED",
            metadata_json={"confirmation_origin": "MANUAL_CONFIRMED"},
        )
        db.add(mention)
        db.commit()
        assert resolve_mentions_with_amap(db, Settings(_env_file=None), [mention]) == (1, 0)
        assert mention.resolution_status == "CONFIRMED"


def test_negative_reference_is_not_promoted_to_review(app_and_session):
    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/negative-reference")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator)
        db.add(asset)
        db.flush()
        mention = PlaceMention(
            video_asset_id=asset.id,
            name="背景公园",
            visit_intent="NOT_RECOMMENDED",
            poi_policy="REFERENCE_ONLY",
            metadata_json={},
        )
        db.add(mention)
        db.commit()
        assert resolve_mentions_with_amap(db, Settings(_env_file=None), [mention]) == (0, 0)
        assert mention.poi_policy == "REFERENCE_ONLY" and mention.resolution_status == "SKIPPED"


def test_search_cannot_overwrite_a_concurrent_revision(client, app_and_session, monkeypatch):
    from zhijian.api.router import get_secret_store

    app, factory = app_and_session
    app.dependency_overrides[get_secret_store] = lambda: SimpleNamespace(get=lambda _: "fixture")
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/search-race")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator)
        db.add(asset)
        db.flush()
        mention = PlaceMention(
            video_asset_id=asset.id,
            name="翠湖",
            raw_name="翠湖",
            suggested_name="翠湖",
            city_hint="昆明市",
            poi_policy="RESOLVE",
            place_type="PARK",
            resolution_status="REVIEW",
            metadata_json={},
        )
        db.add(mention)
        db.commit()
        mention_id = mention.id

    class Provider:
        def __init__(self, _key):
            pass

        def search(self, *_args, **_kwargs):
            with factory() as concurrent:
                item = concurrent.get(PlaceMention, mention_id)
                item.revision = 7
                item.metadata_json = {"concurrent": True}
                concurrent.commit()
            return [poi()]

    monkeypatch.setattr("zhijian.api.router.AMapPOIProvider", Provider)
    response = client.post(
        f"/api/travel/place-mentions/{mention_id}/poi-search",
        json={"query": "翠湖公园", "expected_revision": 0},
    )
    assert response.status_code == 409
    with factory() as db:
        mention = db.get(PlaceMention, mention_id)
        assert mention.revision == 7 and mention.metadata_json == {"concurrent": True}
        assert db.scalar(select(PlaceMention.id).where(PlaceMention.id == mention_id))


def test_confirm_reuses_mixed_case_provider_and_blocks_tombstones(client, app_and_session):
    from zhijian.db.models import Place, PlaceDeletionTombstone

    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/identity")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator)
        db.add(asset)
        db.flush()
        existing = Place(
            name="翠湖公园",
            place_type="PARK",
            latitude=25.03,
            longitude=102.7,
            external_provider="AMap",
            external_poi_id="p",
        )
        db.add(existing)
        db.flush()
        place_id = existing.id
        candidate = {"provider_id": "p", "name": "翠湖公园", "latitude": 25.03, "longitude": 102.7}
        mention = PlaceMention(
            video_asset_id=asset.id,
            name="翠湖",
            poi_policy="RESOLVE",
            metadata_json={"poi_candidates": [candidate]},
            resolution_status="REVIEW",
        )
        db.add(mention)
        db.commit()
        mention_id = mention.id
    url = f"/api/travel/place-mentions/{mention_id}/confirm"
    result = client.post(url, json={"poi_id": "p", "expected_revision": 0})
    assert result.status_code == 200 and result.json()["place_id"] == place_id
    with factory() as db:
        assert len(db.scalars(select(Place).where(Place.external_poi_id == "p")).all()) == 1
        db.add(
            PlaceDeletionTombstone(external_provider="AMap", external_poi_id="p", former_place_id=place_id)
        )
        db.commit()
    assert client.post(url, json={"poi_id": "p", "expected_revision": 1}).status_code == 409


def test_provider_configuration_error_does_not_fan_out(monkeypatch):
    from zhijian.providers.amap import AMapPOIProvider, AMapProviderError
    from zhijian.services.video_support import _rank_poi_candidates

    class Provider:
        calls = 0

        def search(self, *_args, **_kwargs):
            self.calls += 1
            raise AMapProviderError("INVALID_USER_KEY")

    provider = Provider()
    mention = PlaceMention(
        id="m",
        name="翠湖",
        raw_name="翠湖",
        suggested_name="翠湖公园",
        city_hint="昆明市",
        province_hint="云南省",
        metadata_json={},
    )
    result = _rank_poi_candidates(provider, mention)
    assert provider.calls == 1 and result.trace["status"] == "FAILED"
    for location in ["nan,25", "102,inf", "200,25"]:
        assert AMapPOIProvider._candidate({"id": "p", "name": "翠湖", "location": location}) is None


def test_geo_context_never_crosses_submission(app_and_session):
    from zhijian.db.models import Segment, Snapshot
    from zhijian.services.video_support import _assign_geo_sessions, _poi_score

    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/context-isolation")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator)
        db.add(asset)
        db.flush()
        snapshot = Snapshot(source_id=source.id, content_hash="context")
        db.add(snapshot)
        db.flush()
        segments = [
            Segment(snapshot_id=snapshot.id, ordinal=i, text="翠湖", locator_json={}) for i in range(2)
        ]
        db.add_all(segments)
        db.flush()
        first = PlaceMention(
            video_asset_id=asset.id,
            submission_job_id="submission-a",
            name="翠湖",
            city_hint="昆明市",
            content_unit_id="unit1",
            segment_ids_json=[segments[0].id],
            metadata_json={},
        )
        second = PlaceMention(
            video_asset_id=asset.id,
            submission_job_id="submission-b",
            name="翠湖",
            content_unit_id="unit1",
            segment_ids_json=[segments[1].id],
            metadata_json={},
        )
        db.add_all([first, second])
        db.flush()
        _assign_geo_sessions(db, [first, second])
        assert second.metadata_json["resolver_context"]["geo_session_city"] == ""
        _, _, explanation = _poi_score(second, poi(), [first, second])
        assert explanation["cross_place_context"] == []


def test_anchor_binding_and_conflict_are_checked_before_viewport(client, app_and_session):
    from zhijian.db.models import Destination, Segment, Snapshot
    from zhijian.services.area_anchors import bind_representative_anchor, representative_anchor_valid

    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/anchor-scope")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator)
        db.add(asset)
        db.flush()
        snap = Snapshot(
            source_id=source.id, content_hash="anchor", metadata_json={"video_asset_id": asset.id}
        )
        db.add(snap)
        db.flush()
        segment = Segment(snapshot_id=snap.id, ordinal=0, text="推荐昆明市", locator_json={})
        destination = Destination(
            name="昆明市",
            canonical_name="昆明市",
            scope_type="CITY",
            province="云南省",
            city="昆明市",
            district="",
        )
        db.add_all([segment, destination])
        db.flush()
        destination_id = destination.id
        mentions = []
        for provider_id, longitude in [("one", 102.7), ("conflicting", 130.0)]:
            mention = PlaceMention(
                video_asset_id=asset.id,
                name="昆明市",
                raw_name="昆明市",
                suggested_name="昆明市",
                poi_policy="AREA_RESOLVE",
                subject_role="PRIMARY",
                visit_intent="RECOMMENDED",
                resolution_status="AREA_RESOLVED",
                destination_id=destination.id,
                quote="推荐昆明市",
                segment_ids_json=[segment.id],
                metadata_json={},
            )
            db.add(mention)
            db.flush()
            anchor = bind_representative_anchor(
                {
                    "kind": "GOVERNMENT_SEAT",
                    "provider_id": provider_id,
                    "name": "昆明市人民政府",
                    "longitude": longitude,
                    "latitude": 25.0,
                    "coordinate_system": "GCJ02",
                },
                destination,
                mention,
                asset.source_id,
                snap.id,
            )
            mention.metadata_json = {"representative_anchor": anchor}
            assert representative_anchor_valid(anchor, destination, mention, source.id)
            mentions.append(mention)
        db.commit()
        first_id = mentions[0].id
        second_id = mentions[1].id
    data = client.get("/api/travel/map", params={"bbox": "100,20,110,30"}).json()
    assert not any(m["id"] == destination_id for m in data["markers"])
    with factory() as db:
        db.get(PlaceMention, second_id).extraction_status = "USER_REJECTED"
        db.commit()
    data = client.get("/api/travel/map", params={"bbox": "100,20,110,30"}).json()
    assert any(m["id"] == destination_id for m in data["markers"])
    with factory() as db:
        db.get(PlaceMention, first_id).quote = "改动后的引文"
        db.commit()
    data = client.get("/api/travel/map", params={"bbox": "100,20,110,30"}).json()
    assert not any(m["id"] == destination_id for m in data["markers"])


def test_ranking_uses_unclamped_scores_and_distant_children_still_compete():
    from zhijian.services.video_support import _poi_competitor, _rank_poi_candidates

    class Provider:
        def search(self, *_args, **_kwargs):
            return [
                replace(poi(), provider_id="low", name="国家博物馆一", typecode="140000"),
                replace(
                    poi(),
                    provider_id="high",
                    name="国家博物馆乙",
                    address="昆明市五华区明路",
                    typecode="140000",
                ),
            ]

    mention = PlaceMention(
        id="m",
        video_asset_id="v",
        name="国家博物馆",
        raw_name="国家博物馆",
        suggested_name="国家博物馆",
        place_type="MUSEUM",
        city_hint="昆明市",
        province_hint="云南省",
        metadata_json={"resolver_context": {"district_hint": "五华区", "nearby_landmarks": ["明路"]}},
    )
    result = _rank_poi_candidates(Provider(), mention)
    assert result[0].provider_id == "high"
    assert result[0].score == result[1].score == 100
    parent = replace(poi(), match_explanation={"relation_to_mention": "SAME"})
    far_child = replace(
        poi(),
        provider_id="far",
        name="翠湖公园-入口",
        longitude=104.5,
        match_explanation={"relation_to_mention": "CHILD"},
    )
    assert _poi_competitor([parent, far_child]) is far_child


def test_full_page_is_not_evidence_of_complete_candidate_coverage():
    from zhijian.services.video_support import _poi_review_reasons, _rank_poi_candidates

    class Provider:
        def search(self, *_args, **_kwargs):
            return [replace(poi(), provider_id=str(i)) for i in range(20)]

    mention = PlaceMention(
        id="m",
        name="翠湖公园",
        raw_name="翠湖公园",
        suggested_name="翠湖公园",
        place_type="PARK",
        city_hint="昆明市",
        metadata_json={},
    )
    result = _rank_poi_candidates(Provider(), mention)
    assert result.trace["status"] == "PARTIAL" and result.trace["truncated"]
    assert "查询结果不完整" in _poi_review_reasons(result[0], None)


def test_review_actions_are_blocked_while_owner_job_is_running(client, app_and_session):
    from zhijian.db.models import Job

    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/active-job")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator)
        job = Job(job_type="TRAVEL", status="RUNNING", payload_json={"source_id": source.id})
        db.add_all([asset, job])
        db.flush()
        mention = PlaceMention(
            video_asset_id=asset.id,
            submission_job_id=job.id,
            name="翠湖",
            poi_policy="RESOLVE",
            resolution_status="REVIEW",
            metadata_json={
                "poi_candidates": [
                    {"provider_id": "p", "name": "翠湖公园", "longitude": 102.7, "latitude": 25.03}
                ]
            },
        )
        db.add(mention)
        db.commit()
        mention_id = mention.id
    base = f"/api/travel/place-mentions/{mention_id}"
    for path, payload in [
        ("/poi-search", {"query": "翠湖", "expected_revision": 0}),
        ("/confirm", {"poi_id": "p", "expected_revision": 0}),
        ("/reject", {}),
    ]:
        response = client.post(base + path, json=payload)
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "PLACE_JOB_ACTIVE"
    with factory() as db:
        assert db.get(PlaceMention, mention_id).revision == 0


def test_reference_and_invalid_evidence_do_not_supply_geo_context(app_and_session):
    from zhijian.db.models import Segment, Snapshot
    from zhijian.services.video_support import _assign_geo_sessions

    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/geo-barriers")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator)
        db.add(asset)
        db.flush()
        snapshot = Snapshot(source_id=source.id, content_hash="geo-barriers")
        db.add(snapshot)
        db.flush()
        segments = [
            Segment(snapshot_id=snapshot.id, ordinal=i, text="原文", locator_json={}) for i in range(4)
        ]
        db.add_all(segments)
        db.flush()
        mentions = [
            PlaceMention(
                video_asset_id=asset.id,
                name=f"地点{i}",
                poi_policy="RESOLVE",
                segment_ids_json=[segment.id],
                metadata_json={},
            )
            for i, segment in enumerate(segments)
        ]
        mentions[0].city_hint = "昆明市"
        mentions[1].city_hint = "大理市"
        mentions[1].poi_policy = "REFERENCE_ONLY"
        mentions[2].city_hint = "丽江市"
        db.add_all(mentions)
        db.flush()
        _assign_geo_sessions(db, mentions[:3])
        assert mentions[2].metadata_json["resolver_context"]["geo_session_city"] == "丽江市"
        mentions[2].city_hint = ""
        _assign_geo_sessions(db, mentions[:3])
        assert mentions[2].metadata_json["resolver_context"]["geo_session_city"] == "昆明市"
        _assign_geo_sessions(db, mentions, untrusted_ids={mentions[2].id})
        assert mentions[3].metadata_json["resolver_context"]["geo_session_city"] == ""


def test_area_anchor_reuse_rechecks_binding_and_counts_provider_calls(app_and_session):
    from zhijian.db.models import Segment, Snapshot
    from zhijian.services.video_support import materialize_destinations

    class Provider:
        request_count = cache_hit_count = 0

        def search(self, *_args, **_kwargs):
            self.request_count += 1
            return [
                POICandidate(
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
            ]

        def detail(self, _id):
            self.request_count += 1
            return POICandidate(
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

    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/area-reuse")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator)
        db.add(asset)
        db.flush()
        snapshot = Snapshot(
            source_id=source.id, content_hash="area-reuse", metadata_json={"video_asset_id": asset.id}
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
            quote="推荐昆明市",
            segment_ids_json=[segment.id],
            metadata_json={},
        )
        db.add(mention)
        db.flush()
        provider = Provider()
        metrics = {"amap_request_count": 3}
        materialize_destinations(db, asset, [mention], provider, metrics=metrics)
        assert metrics["amap_request_count"] == 5
        assert mention.metadata_json["representative_anchor"]["provider_id"] == "government"
        materialize_destinations(db, asset, [mention], provider, metrics=metrics)
        assert metrics["amap_request_count"] == 5 and provider.request_count == 2
        mention.quote = "源文没有这一句话"
        materialize_destinations(db, asset, [mention], provider, metrics=metrics)
        assert "representative_anchor" not in mention.metadata_json
        assert provider.request_count == 2


def test_unscoped_regions_do_not_merge_and_natural_area_keeps_its_name(app_and_session):
    from zhijian.db.models import Destination
    from zhijian.services.video_support import materialize_destinations

    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/area-identity")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator)
        db.add(asset)
        db.flush()
        uncertain = PlaceMention(
            video_asset_id=asset.id,
            name="朝阳区",
            raw_name="朝阳区",
            poi_policy="AREA_RESOLVE",
            province_hint="",
            city_hint="",
            metadata_json={},
        )
        natural = PlaceMention(
            video_asset_id=asset.id,
            name="滇池",
            raw_name="滇池",
            poi_policy="AREA_RESOLVE",
            province_hint="云南省",
            city_hint="昆明市",
            metadata_json={},
        )
        db.add_all([uncertain, natural])
        db.flush()
        created, _ = materialize_destinations(db, asset, [uncertain, natural])
        assert created == 1 and uncertain.destination_id is None
        assert uncertain.resolution_status == "AREA_UNRESOLVED"
        destination = db.get(Destination, natural.destination_id)
        assert destination.canonical_name == "滇池" and destination.scope_type == "OTHER"


def test_ambiguous_area_units_do_not_attach_places_to_last_area(app_and_session):
    from zhijian.db.models import Place
    from zhijian.services.video_support import materialize_destinations

    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/ambiguous-area")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator)
        place = Place(name="候选景点", place_type="PARK", latitude=25.0, longitude=102.0)
        db.add_all([asset, place])
        db.flush()
        areas = [
            PlaceMention(
                video_asset_id=asset.id,
                name=name,
                raw_name=name,
                city_hint=name,
                province_hint="云南省",
                poi_policy="AREA_RESOLVE",
                content_unit_id="shared",
                metadata_json={},
            )
            for name in ["昆明市", "丽江市"]
        ]
        action = PlaceMention(
            video_asset_id=asset.id,
            name="候选景点",
            resolution_status="CONFIRMED",
            place_id=place.id,
            content_unit_id="shared",
            metadata_json={},
        )
        db.add_all([*areas, action])
        db.flush()
        _, linked = materialize_destinations(db, asset, [*areas, action])
        assert linked == 0


def test_empty_auto_search_does_not_offer_stale_candidates(app_and_session, monkeypatch):
    from zhijian.db.models import Segment, Snapshot

    class Provider:
        def __init__(self, *_args, **_kwargs):
            pass

        def search(self, *_args, **_kwargs):
            return []

    monkeypatch.setattr("zhijian.services.video_support.AMapPOIProvider", Provider)
    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/stale-candidates")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator)
        db.add(asset)
        db.flush()
        snapshot = Snapshot(
            source_id=source.id, content_hash="stale", metadata_json={"video_asset_id": asset.id}
        )
        db.add(snapshot)
        db.flush()
        segment = Segment(snapshot_id=snapshot.id, ordinal=0, text="推荐翠湖公园", locator_json={})
        db.add(segment)
        db.flush()
        mention = PlaceMention(
            video_asset_id=asset.id,
            name="翠湖公园",
            raw_name="翠湖公园",
            suggested_name="翠湖公园",
            city_hint="昆明市",
            place_type="PARK",
            quote="推荐翠湖公园",
            segment_ids_json=[segment.id],
            poi_policy="RESOLVE",
            metadata_json={"poi_candidates": [{"provider_id": "obsolete"}]},
        )
        db.add(mention)
        db.commit()
        assert resolve_mentions_with_amap(db, Settings(_env_file=None), [mention], "fixture") == (0, 1)
        assert mention.resolution_status == "UNRESOLVED"
        assert mention.metadata_json["poi_candidates"] == []
        assert mention.metadata_json["reason_codes"] == ["POI_SEARCH_EMPTY"]
