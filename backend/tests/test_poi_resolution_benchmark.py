from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from zhijian.core.config import Settings
from zhijian.db.models import PlaceMention, Segment, Snapshot, Source, VideoAsset
from zhijian.providers.amap import POICandidate
from zhijian.services.video_support import (
    _assign_geo_sessions,
    _category_compatibility,
    _nearby_radius,
    _poi_review_reasons,
    _poi_score,
    _rank_poi_candidates,
    _resolver_v2_shadow,
    resolve_mentions_with_amap,
)


def _runner():
    path = Path(__file__).parents[2] / "scripts" / "run_poi_resolution_benchmark.py"
    spec = importlib.util.spec_from_file_location("run_poi_resolution_benchmark", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_poi_resolution_golden_enforces_precision_first_gate() -> None:
    path = Path(__file__).parents[2] / "dev docs" / "benchmark" / "poi-resolution-golden-v1.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    result = _runner().evaluate(cases)

    assert len(cases) >= 10
    assert result["candidate_recall_at_3"] == 1
    assert result["wrong_confirm_count"] == 0
    assert result["auto_confirm_precision"] == 1
    assert {item["sample_id"]: item["status"] for item in result["statuses"]} == {
        str(case["sample_id"]): str(case["expected"]["status"]) for case in cases
    }


def test_place_type_mapping_exposes_stable_review_reason_codes() -> None:
    assert _category_compatibility("NEIGHBORHOOD", "120300") == "STRONG"
    assert _category_compatibility("NEIGHBORHOOD", "190000") == "WEAK"
    assert _category_compatibility("SCENIC_AREA", "100000") == "INCOMPATIBLE"
    assert _category_compatibility("OTHER", "110000") == "UNMAPPED"

    candidate = POICandidate(
        provider_id="other",
        name="示例地点",
        address="昆明市",
        province="云南省",
        city="昆明市",
        district="",
        longitude=102.7,
        latitude=25.0,
        typecode="110000",
        score=90,
        match_explanation={
            "name_match": 1.0,
            "city_match": True,
            "coordinate_valid": True,
            "category_match": False,
            "category_compatibility": "UNMAPPED",
        },
    )
    assert "地点类型尚无可靠分类映射" in _poi_review_reasons(candidate, None)
    assert candidate.match_explanation["review_reason_codes"] == ["CATEGORY_UNMAPPED"]


def test_resolver_v2_shadow_is_deterministic_without_changing_v1_decision() -> None:
    mention = PlaceMention(
        id="pm-shadow",
        video_asset_id="vid-shadow",
        name="翠湖公园",
        raw_name="翠湖公园",
        suggested_name="翠湖公园",
        city_hint="昆明市",
        place_type="PARK",
    )
    candidates = [
        POICandidate(
            "cuihu",
            "翠湖公园",
            "昆明市五华区",
            "云南省",
            "昆明市",
            "五华区",
            102.7,
            25.05,
            "110000",
        ),
        POICandidate(
            "cuihu-other",
            "翠湖公园",
            "玉溪市",
            "云南省",
            "玉溪市",
            "",
            102.5,
            24.4,
            "110000",
        ),
    ]
    for candidate in candidates:
        candidate.score, candidate.match_reasons, candidate.match_explanation = _poi_score(
            mention, candidate, []
        )
    candidates.sort(key=lambda item: (-item.score, item.name))

    assert _poi_review_reasons(candidates[0], candidates[1]) == []
    first = _resolver_v2_shadow(mention, candidates)
    assert first == _resolver_v2_shadow(mention, candidates)
    assert first["decision"] == "AUTO_STRONG"
    assert first["features"]["candidate_gap"] >= 15


def test_geo_sessions_keep_context_local_to_a_region_transition(app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/geo")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator)
        db.add(asset)
        snapshot = Snapshot(source_id=source.id, content_hash="geo")
        db.add(snapshot)
        db.flush()
        segments = [
            Segment(snapshot_id=snapshot.id, ordinal=index, text=f"segment {index}")
            for index in range(4)
        ]
        db.add_all(segments)
        db.flush()
        mentions = [
            PlaceMention(
                video_asset_id=asset.id,
                name="翠湖",
                city_hint="昆明市",
                segment_ids_json=[segments[0].id],
            ),
            PlaceMention(video_asset_id=asset.id, name="文林街", segment_ids_json=[segments[1].id]),
            PlaceMention(
                video_asset_id=asset.id,
                name="古城",
                city_hint="大理市",
                segment_ids_json=[segments[2].id],
            ),
            PlaceMention(video_asset_id=asset.id, name="洋人街", segment_ids_json=[segments[3].id]),
        ]
        db.add_all(mentions)
        db.flush()
        _assign_geo_sessions(db, mentions)

        contexts = [item.metadata_json["resolver_context"] for item in mentions]
        assert contexts[0]["geo_session_id"] == contexts[1]["geo_session_id"]
        assert contexts[2]["geo_session_id"] == contexts[3]["geo_session_id"]
        assert contexts[0]["geo_session_id"] != contexts[2]["geo_session_id"]
        assert contexts[1]["geo_session_city"] == "昆明市"
        assert contexts[3]["geo_session_city"] == "大理市"


def test_contextual_candidate_generation_records_consensus_and_negative_evidence() -> None:
    class Provider:
        def __init__(self) -> None:
            self.radii: list[int] = []

        def search(self, *_args, **_kwargs):
            return [
                POICandidate(
                    "market", "篆新农贸市场", "昆明市西山区", "云南省", "昆明市", "西山区",
                    102.68, 25.03, "060700",
                ),
                POICandidate(
                    "other-city", "篆新农贸市场", "曲靖市", "云南省", "曲靖市", "", 103.8,
                    25.5, "060700",
                ),
            ]

        def around(self, _longitude, _latitude, _keywords, *, radius):
            self.radii.append(radius)
            return []

    provider = Provider()
    mention = PlaceMention(
        id="pm-context",
        video_asset_id="vid-context",
        name="篆新市场",
        raw_name="篆新市场",
        suggested_name="篆新农贸市场",
        place_type="MARKET",
        metadata_json={
            "resolver_context": {
                "aliases": ["篆新菜市场"],
                "geo_session_city": "昆明市",
                "nearby_relation": "附近",
                "nearby_anchor": {"longitude": 102.68, "latitude": 25.03},
            }
        },
    )
    candidates = _rank_poi_candidates(provider, mention, [mention])

    assert _nearby_radius("附近") == 700
    assert provider.radii == [700]
    assert candidates[0].provider_id == "market"
    assert candidates[0].match_explanation["query_consensus_count"] >= 2
    assert candidates[0].match_explanation["query_diversity"] >= 1
    assert "CROSS_CITY_CONFLICT" not in candidates[0].match_explanation["negative_evidence"]
    assert "CROSS_CITY_CONFLICT" in candidates[1].match_explanation["negative_evidence"]


def test_re_resolution_never_overwrites_a_manual_confirmation(app_and_session, monkeypatch) -> None:
    _, factory = app_and_session

    class Provider:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def search(self, *_args, **_kwargs):
            raise AssertionError("manual confirmation must skip external resolution")

    monkeypatch.setattr("zhijian.services.video_support.AMapPOIProvider", Provider)
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/manual-replay")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator)
        db.add(asset)
        db.flush()
        mention = PlaceMention(
            video_asset_id=asset.id,
            name="翠湖公园",
            resolution_status="CONFIRMED",
            metadata_json={"confirmation_origin": "MANUAL_CONFIRMED"},
        )
        db.add(mention)
        db.commit()

        assert resolve_mentions_with_amap(db, Settings(_env_file=None), [mention], "fixture") == (1, 0)
        assert mention.metadata_json["confirmation_origin"] == "MANUAL_CONFIRMED"
