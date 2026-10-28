"""P0_CRITICAL: frozen source, mocked extraction boundary, no model-quality claims."""

import hashlib
import io
import json
import re
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from zhijian.db.models import (
    AINote,
    AINoteVersion,
    GroundedMapArtifact,
    Place,
    PlaceMention,
    RouteDraft,
    RouteDraftItem,
    Source,
    Transcript,
    VideoAsset,
)
from zhijian.services.recommendation_intent import assess
from zhijian.services.route_guides import extract_routes, validate_route
from zhijian.services.travel_recommendations import visit_window_summary
from zhijian.services.travel_semantics import classify_entity, temporal_semantics
from zhijian.services.video_support import _months_in_text, _visit_windows_from_candidate

FIXTURE = Path(__file__).parent / "fixtures/travel_pipeline/yunnan_bv16yem6reyx"
REFERENCE = json.loads((FIXTURE / "YUNNAN_TRANSCRIPT_ZHIJIAN_SIMULATED_RESULT_20261028.json").read_text())


def transcript():
    return {
        f"s{i}": m[3]
        for i, m in enumerate(
            re.finditer(
                r"\[(\d+:\d+) - (\d+:\d+)\] (.+)",
                (FIXTURE / "zhijian-transcript-BV16Yem6REyX.txt").read_text(),
            )
        )
    }


def window(**kwargs):
    return SimpleNamespace(
        period_type=kwargs.get("period_type", "BEST_VISIT"),
        suitability=kwargs.get("suitability", "INFORMATIONAL"),
        provenance=kwargs.get("provenance", "SOURCE_FACT"),
        month=kwargs.get("month"),
        season=kwargs.get("season", "WINTER"),
        month_segment=None,
        day_time_slot=None,
        source_id="src",
        segment_ids_json=["s"],
        source_text=kwargs.get("source_text", "冬季可游览"),
    )


def test_fixture_provenance_and_reference_limits():
    provenance = json.loads((FIXTURE / "provenance.json").read_text())
    assert not provenance["reference_is_verified_gold"]
    for name, digest in provenance["files"].items():
        assert hashlib.sha256((FIXTURE / name).read_bytes()).hexdigest() == digest
    assert len(REFERENCE["place_candidates"]) == 71
    assert len(REFERENCE["route_guides"]) == 11


@pytest.mark.parametrize(
    "kind,identity",
    [
        ("PLACE_UNCERTAIN", "UNRESOLVED_NAME"),
        ("AREA_DESTINATION", "AREA"),
        ("GENERIC_FEATURE", "GENERIC"),
        ("LINEAR_FEATURE", "LINEAR"),
    ],
)
def test_A_entity_classification_never_implies_a_pin(kind, identity):
    result = classify_entity({"raw_name": "原词", "kind": kind, "visit_intent": "RECOMMENDED"})
    assert result["identity"] == identity
    assert not result["eligible_for_poi"]


def test_A01_uncertain_and_A04_reference_keep_raw_words():
    assert classify_entity({"raw_name": "支子罗", "review_status": "NEEDS_REVIEW"})["raw_name"] == "支子罗"
    assert not classify_entity(
        {"raw_name": "小中甸", "subject_role": "REFERENCE", "visit_intent": "NEUTRAL"}
    )["eligible_for_poi"]


@pytest.mark.parametrize(
    "quote,scope,activity,precision",
    [
        ("冬天看到日照金山的概率更高", "PLACE", "VIEWING", "SEASON"),
        ("十一月到次年三月是最适合来的时候", "AREA", "GENERAL_VISIT", "MONTH"),
        ("一月到四月灌水", "PLACE", "VIEWING", "MONTH"),
        ("二月到三月油菜花", "PLACE", "VIEWING", "MONTH"),
        ("秋天的时候能看到湖面上的水性杨花", "PLACE", "VIEWING", "SEASON"),
        ("冬天看红嘴鸥", "PLACE", "VIEWING", "SEASON"),
        ("部分路段冬天还会封路", "ROAD_SECTION", "SELF_DRIVE", "SEASON"),
        ("秋冬季节较推荐", "AREA", "GENERAL_VISIT", "SEASON"),
        ("普通游客就不建议骑马了", "PLACE", "HORSE_RIDING", "QUALITATIVE"),
        ("西线不能自驾", "ROAD_SECTION", "SELF_DRIVE", "QUALITATIVE"),
    ],
)
def test_B_C_scoped_time_activity(quote, scope, activity, precision):
    actual = temporal_semantics(quote, scope=scope)
    assert actual["scope"] == scope
    assert actual["activity"] == activity
    assert actual["precision"] == precision
    assert actual["start"] is None or "day" not in actual["start"]


def test_B02_cross_year_and_exact_date_precision():
    assert _months_in_text("十一月到次年三月") == [11, 12, 1, 2, 3]
    assert temporal_semantics("十一月到次年三月")["cross_year"]
    assert temporal_semantics("12月20日到次年1月5日")["precision"] == "DAY"
    assert temporal_semantics("2月31日到3月5日")["precision"] != "DAY"


def test_C05_uncertain_road_number_is_not_corrected():
    raw = "自驾可以走S二二幺"
    assert temporal_semantics(raw)["interpretation_status"] == "NEEDS_REVIEW"
    assert raw.endswith("S二二幺")


def test_E01_background_does_not_raise_timing_score():
    assert visit_window_summary([window()])["state"] == "UNKNOWN"
    assert (
        visit_window_summary([window(suitability="RECOMMENDED", provenance="SEMANTIC_CONTEXT")])["state"]
        == "UNKNOWN"
    )


@pytest.mark.parametrize(
    "w",
    [
        window(period_type="FISHING_CLOSURE", suitability="RESTRICTED", source_text="冬季禁渔期"),
        window(period_type="SEASONAL_CLOSURE", suitability="RESTRICTED", source_text="部分路段冬天封路"),
    ],
)
def test_B07_no_whole_destination_closure(w):
    assert visit_window_summary([w], 1)["state"] != "CLOSED"


def test_C01_riding_is_local_negative():
    quote = "拉市海。来这儿的话，普通游客就不建议骑马了，在湖边溜达溜达就行"
    result = assess(
        {"name": "拉市海", "raw_name": "拉市海", "entity_id": "e", "segment_ids": ["s"], "quote": quote},
        {"s": quote},
    )
    assert result["status"] != "NOT_RECOMMENDED"


def test_ambiguous_month_does_not_broadcast_to_shared_points():
    # Extraction uses named sentences for a shared Segment; anonymous time belongs to neither.
    texts = {"s": "十月最好。甲山与乙湖都在附近"}
    scoped = {
        sid: "。".join(p for p in re.split(r"[。；，]", text) if "甲山" in p and "乙湖" not in p)
        for sid, text in texts.items()
    }
    assert _visit_windows_from_candidate({}, ["s"], scoped) == []


def route_claims():
    return json.loads((FIXTURE / "grounded_routes.json").read_text())


@pytest.mark.parametrize("case_index", range(12))
def test_D_frozen_grounded_routes(case_index):
    claim = route_claims()[case_index]
    route = validate_route(claim["route"], claim, transcript())
    assert route is not None
    assert [s["raw_name"] for s in route["stops"]] == claim["route"]["stops"]
    assert route["mode"] == claim["route"]["mode"]
    assert route["navigation"] is None and not route["is_closed_loop_verified"]
    assert not route["road_covers_all_stops"]
    assert all(s["place_id"] is None for s in route["stops"])


def test_D01_D02_D03_order_and_related_road():
    claims = route_claims()
    routes = extract_routes(claims, transcript())
    assert [s["raw_name"] for s in routes[0]["stops"]] == ["六库", "贡山", "丙中洛"]
    assert "独龙江" not in [s["raw_name"] for s in routes[0]["stops"]]
    assert routes[2]["id"] in routes[1]["related_guide_ids"]
    assert routes[1]["id"] in routes[2]["related_guide_ids"]
    invalid = {**claims[0], "route": {**claims[0]["route"], "stops": ["六库", "丙中洛", "贡山"]}}
    assert validate_route(invalid["route"], invalid, transcript()) is None
    invalid = {**claims[0], "supporting_quote": "虚构引文"}
    assert validate_route(invalid["route"], invalid, transcript()) is None


def test_api_E02_E03_E04_compatibility_and_dry_run(client, app_and_session):
    _, factory = app_and_session
    place_id = client.get("/api/travel/map?zoom=8").json()["markers"][0]["id"]
    manual = client.post(
        f"/api/travel/places/{place_id}/visit-windows",
        json={
            "month": 10,
            "period_type": "BEST_VIEWING",
            "suitability": "INFORMATIONAL",
            "source_text": "十月",
        },
    )
    assert manual.json()["semantics"]["purpose"] == "VIEWING"
    before = client.get("/api/travel/route-drafts").json()
    assert client.get("/api/travel/route-guides").json() == []
    assert client.get("/api/travel/history-audit").json()["writes"] == 0
    for fmt in ["json", "csv", "geojson"]:
        assert client.post("/api/travel/export?format=" + fmt).status_code == 200
    response = client.get("/api/travel/export-v2")
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        assert set(z.namelist()) == {"manifest.json", "places.json", "routes.json"}
        assert json.loads(z.read("manifest.json"))["schema_version"] == "travel_export_v2"
    assert client.get("/api/travel/route-drafts").json() == before
    with factory() as db:
        assert db.scalars(select(RouteDraft)).all() is not None


def test_route_persistence_version_binding_copy_and_user_order(client, app_and_session):
    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="fixture://yunnan-routes")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url="fixture://yunnan-routes", title="云南离线夹具")
        db.add(asset)
        db.flush()
        tr = Transcript(video_asset_id=asset.id, version=1, source_kind="FIXTURE")
        db.add(tr)
        db.flush()
        note = AINote(video_asset_id=asset.id)
        db.add(note)
        db.flush()
        v = AINoteVersion(ai_note_id=note.id, version=1, markdown="离线", transcript_version=1)
        db.add(v)
        db.flush()
        note.current_version_id = v.id
        guides = extract_routes(route_claims(), transcript())
        a = GroundedMapArtifact(
            video_asset_id=asset.id,
            transcript_id=tr.id,
            transcript_version=1,
            content_hash="f",
            semantic_hash="f",
            prompt_version="test",
            supplement_hash="",
            provider="FIXTURE",
            model="FIXTURE",
            semantic_options_json={"route_guides": guides},
        )
        db.add(a)
        db.flush()
        v.grounded_map_artifact_id = a.id
        for stop in guides[0]["stops"]:
            p = Place(
                name=stop["raw_name"],
                canonical_name=stop["raw_name"],
                place_type="TOWN",
                latitude=0,
                longitude=0,
                resolution_status="CONFIRMED",
            )
            db.add(p)
            db.flush()
            db.add(
                PlaceMention(
                    video_asset_id=asset.id,
                    ai_note_version_id=v.id,
                    name=p.name,
                    raw_name=p.name,
                    segment_ids_json=guides[0]["evidence"]["segment_ids"],
                    place_id=p.id,
                    resolution_status="CONFIRMED",
                )
            )
        db.commit()
        nid, vid = note.id, v.id
    response = client.get("/api/travel/route-guides").json()
    assert len(response) == len(guides)
    g = response[0]
    assert all(s["place_id"] for s in g["stops"])
    archive_response = client.get("/api/travel/export-v2")
    with zipfile.ZipFile(io.BytesIO(archive_response.content)) as archive:
        place_file = json.loads(archive.read("places.json"))
        assert len([c for c in place_file["source_candidates"] if c["version_id"] == vid]) == 3
        assert json.loads(archive.read("routes.json"))["author_guides"][0]["version_id"] == vid
    copy = client.post(
        "/api/travel/route-guides/copy", json={"note_id": nid, "guide_id": g["guide_id"], "version_id": vid}
    )
    assert copy.status_code == 200
    rid = copy.json()["id"]
    with factory() as db:
        items = db.scalars(
            select(RouteDraftItem)
            .where(RouteDraftItem.route_draft_id == rid)
            .order_by(RouteDraftItem.sort_order)
        ).all()
        original = [i.place_id for i in items]
        a = db.scalar(select(GroundedMapArtifact).where(GroundedMapArtifact.semantic_hash == "f"))
        a.semantic_options_json = {"route_guides": []}
        db.commit()
    assert client.get("/api/travel/route-guides").json() == []
    assert [
        p["id"]
        for p in next(r for r in client.get("/api/travel/route-drafts").json() if r["id"] == rid)["places"]
    ] == original


def test_P0_materialization_is_per_mention_not_video(app_and_session):
    from zhijian.services.video_support import extract_place_mentions

    _, factory = app_and_session
    texts = [
        SimpleNamespace(id="s1", text="甲山十月红叶最好", corrected_text=""),
        SimpleNamespace(id="s2", text="乙湖可以散步", corrected_text=""),
    ]
    with factory() as db:
        source = Source(source_type="URL", locator="fixture://per-mention")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url="fixture://per-mention", title="十月旅行")
        db.add(asset)
        db.flush()
        mentions = extract_place_mentions(
            db,
            SimpleNamespace(),
            asset,
            None,
            texts,
            candidates=[
                {
                    "name": "甲山",
                    "raw_name": "甲山",
                    "segment_ids": ["s1"],
                    "quote": "甲山十月红叶最好",
                    "entity_id": "e1",
                    "visit_intent": "RECOMMENDED",
                    "subject_role": "PRIMARY",
                },
                {
                    "name": "乙湖",
                    "raw_name": "乙湖",
                    "segment_ids": ["s2"],
                    "quote": "乙湖可以散步",
                    "entity_id": "e2",
                    "visit_intent": "RECOMMENDED",
                    "subject_role": "PRIMARY",
                },
            ],
        )
        assert mentions[0].metadata_json["temporal_analysis"]["status"] == "ANALYZED"
        assert mentions[1].metadata_json["temporal_analysis"]["status"] == "NO_TIME_MENTIONED"


def test_all_71_typed_candidates_are_not_71_confirmed_pins():
    output = [classify_entity({**c, "raw_name": c["raw_label"]}) for c in REFERENCE["place_candidates"]]
    assert len(output) == 71
    assert all(
        p["raw_name"] == r["raw_label"] for p, r in zip(output, REFERENCE["place_candidates"], strict=True)
    )
    assert all(
        not p["eligible_for_poi"] for p in output
    )  # Reference annotations have no validated visit intent.


def test_routes_reject_cross_snapshot_order_and_fabricated_conditions():
    claim = route_claims()[0]
    assert (
        validate_route(
            claim["route"], {**claim, "segment_ids": list(reversed(claim["segment_ids"]))}, transcript()
        )
        is None
    )
    invalid = {
        **claim["route"],
        "conditions": [{"subject": "怒江", "quote": "冬季全线关闭", "segment_ids": claim["segment_ids"]}],
    }
    assert validate_route(invalid, claim, transcript()) is None
    invalid = {**claim["route"], "stops": ["六库", "独龙江", "丙中洛"]}
    assert validate_route(invalid, claim, transcript()) is None


def test_C02_source_transport_is_separate_and_does_not_invent_duration():
    from zhijian.services.travel_brief import travel_brief
    from zhijian.services.travel_semantics import scoped_travel_facts

    facts = scoped_travel_facts("这里更适合自驾。", ["s"])
    assert facts[0]["insight_type"] == "ACCESS_MODE"
    assert facts[0]["source_quote"] == "这里更适合自驾"
    brief = travel_brief({"access": [facts[0]["source_quote"]]}, [])
    assert brief["access"] == ["这里更适合自驾"]
    assert "公里" not in str(brief) and "小时" not in str(brief)


def test_E02_route_copy_rejects_stale_or_unresolved_source(client):
    response = client.post(
        "/api/travel/route-guides/copy",
        json={"note_id": "note-old", "guide_id": "rg-old", "version_id": "ntv-old"},
    )
    assert response.status_code == 409
    assert client.get("/api/travel/route-drafts").status_code == 200


def test_real_response_prose_routes_recover_without_model_requests():
    real = json.loads((FIXTURE / "real_response_20261028.json").read_text())
    routes = extract_routes(real["claims"], transcript(), real["entities"])
    assert len(routes) == 13
    expected = [
        ("SELF_DRIVE", ["六库", "贡山", "丙中洛"]),
        ("SELF_DRIVE", ["丽江", "虎跳峡", "小中甸", "独克宗", "梅里雪山"]),
        ("SELF_DRIVE", ["昆明", "大理", "丽江", "香格里拉", "梅里雪山"]),
        ("CYCLING", ["龙龛码头", "喜洲古镇"]),
        ("CYCLING", ["双廊", "洼色"]),
        ("RAIL", ["建水", "石屏"]),
        ("FOOD_THEME", ["芒市", "西双版纳", "建水", "蒙自"]),
        ("SELF_DRIVE", ["昆明", "建水", "元阳"]),
    ]
    for mode, stops in expected:
        assert any(r["mode"] == mode and [s["raw_name"] for s in r["stops"]] == stops for r in routes)
    assert all(r["review_status"] == "NEEDS_REVIEW" and r["navigation"] is None for r in routes)
    assert not any(
        s["raw_name"] in {"可以", "而且消费超级低", "弯道比怒江少很多"} for r in routes for s in r["stops"]
    )


def test_prose_recovery_generalizes_and_never_treats_arbitrary_list_as_a_route():
    from zhijian.services.route_recovery import explicit_route_lists

    texts = {
        "s": (
            "自驾党推荐两条路线：首先是沿海路线G228，甲城、乙镇到丙湾。"
            "然后是山地环线：丁县、戊村、己湖。然后是一个推荐吃货的方向。"
        )
    }
    routes = list(explicit_route_lists(texts))
    assert len(routes) == 2
    assert routes[0][0]["stops"] == ["甲城", "乙镇", "丙湾"]
    assert not list(explicit_route_lists({"s": "甲城、乙镇和丙湾，十月有花。"}))


def test_real_region_anchor_keeps_background_local_and_does_not_truncate_80(app_and_session):
    from zhijian.services.video_support import extract_place_mentions

    real = json.loads((FIXTURE / "real_response_20261028.json").read_text())
    _, factory = app_and_session
    segs = [SimpleNamespace(id=sid, text=text, corrected_text="") for sid, text in transcript().items()]
    with factory() as db:
        source = Source(source_type="URL", locator="fixture://real-replay")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="云南")
        db.add(asset)
        db.flush()
        mentions = extract_place_mentions(
            db,
            SimpleNamespace(),
            asset,
            None,
            segs,
            candidates=real["entities_full"],
            claims=real["claims"],
            content_units=real["content_units"],
        )
        assert len(mentions) > 80
        regional = [m for m in mentions if m.raw_name == "西双版纳"]
        assert any(
            {11, 12, 1, 2, 3} <= {w["month"] for w in m.metadata_json["visit_windows"]} for m in regional
        )
        for m in mentions:
            if m.raw_name in {"曼听公园", "野象谷"}:
                assert not m.metadata_json["visit_windows"]
