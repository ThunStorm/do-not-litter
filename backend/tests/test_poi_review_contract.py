from dataclasses import replace

import pytest

from zhijian.core.config import Settings
from zhijian.db.models import PlaceMention, Segment, Snapshot, Source, VideoAsset
from zhijian.providers.amap import AMapProviderError, POICandidate
from zhijian.services.video_support import _rank_poi_candidates, resolve_mentions_with_amap


def make_mention(db):
    source = Source(source_type="URL", locator="https://example.test/poi-p")
    db.add(source)
    db.flush()
    asset = VideoAsset(source_id=source.id, canonical_url=source.locator)
    db.add(asset)
    db.flush()
    snapshot = Snapshot(source_id=source.id, content_hash="poi-p", metadata_json={"video_asset_id": asset.id})
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
        quote=segment.text,
        segment_ids_json=[segment.id],
        poi_policy="RESOLVE",
        metadata_json={
            "poi_candidates": [
                {"provider_id": "obsolete", "name": "旧候选", "longitude": 102.7, "latitude": 25.03}
            ]
        },
    )
    db.add(mention)
    db.commit()
    return mention


@pytest.mark.parametrize("error", [AMapProviderError("429"), RuntimeError("network failed")])
def test_failed_auto_search_invalidates_old_candidates(app_and_session, client, monkeypatch, error):
    class Provider:
        def __init__(self, *_args, **_kwargs):
            pass

        def search(self, *_args, **_kwargs):
            raise error

    monkeypatch.setattr("zhijian.services.video_support.AMapPOIProvider", Provider)
    _, factory = app_and_session
    with factory() as db:
        mention = make_mention(db)
        original = (mention.raw_name, mention.quote, mention.segment_ids_json[:])
        assert resolve_mentions_with_amap(db, Settings(_env_file=None), [mention], "fixture") == (0, 1)
        assert mention.resolution_status == "REVIEW"
        assert mention.metadata_json["poi_candidates"] == []
        assert mention.metadata_json["reason_codes"] == ["POI_SEARCH_FAILED"]
        assert original == (mention.raw_name, mention.quote, mention.segment_ids_json)
        mention_id, revision = mention.id, mention.revision
    response = client.post(
        f"/api/travel/place-mentions/{mention_id}/confirm",
        json={"poi_id": "obsolete", "expected_revision": revision},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_POI"


def test_search_request_bound_and_duplicate_full_pages():
    value = POICandidate("p", "翠湖公园", "", "云南省", "昆明市", "", 102.7, 25.03, "110000")

    class Provider:
        calls = 0

        def search(self, *_args, **_kwargs):
            self.calls += 1
            return [replace(value, provider_id=str(i)) for i in range(20)]

    provider = Provider()
    mention = PlaceMention(
        name="翠湖",
        suggested_name="翠湖公园",
        raw_name="翠湖园",
        city_hint="昆明市",
        metadata_json={"resolver_context": {"aliases": [f"别名{i}" for i in range(20)]}},
    )
    result = _rank_poi_candidates(provider, mention)
    assert provider.calls == 5
    assert len(result) == 20
    assert result.trace["status"] == "PARTIAL"


def test_review_contract_versions_manual_search_and_job_guards(app_and_session, client):
    from zhijian.db.models import Job, MapMarkerState, Place, PlaceDeletionTombstone
    from zhijian.services.poi_review import poi_review_contract

    _, factory = app_and_session
    with factory() as db:
        mention = make_mention(db)
        mention.resolution_status = "REVIEW"
        mention.metadata_json = {
            "reason_codes": ["POI_SEARCH_EMPTY"],
            "poi_candidates_source": "MANUAL",
            "poi_candidates": [
                {"provider_id": "p", "name": "翠湖公园", "longitude": 102.7, "latitude": 25.03}
            ],
            "manual_search_trace": {"status": "RESULTS", "queries": [{"count": 1}]},
        }
        db.commit()
        contract = poi_review_contract(db, mention)
        assert contract["authority"]["revision"] == mention.revision
        assert contract["evidence"]["valid"]
        assert contract["evidence"]["segment_ids"] == mention.segment_ids_json
        assert contract["classification"] == "MANUAL_RESULTS"
        assert contract["automatic_classification"] == "NO_RESULTS"
        assert contract["search"]["status"] == "RESULTS"
        assert contract["search"]["completeness"] == "UNKNOWN"
        assert contract["allowed_actions"] == ["SEARCH", "REJECT"]
        assert contract["candidate_actions"][0]["allowed_actions"] == ["CONFIRM"]
        job = Job(job_type="TRAVEL", status="COMPLETED", lease_owner="worker")
        db.add(job)
        db.flush()
        mention.submission_job_id = job.id
        db.commit()
        contract = poi_review_contract(db, mention)
        assert contract["blocked_by"] == ["PLACE_JOB_ACTIVE"]
        assert not contract["allowed_actions"]
        assert not contract["candidate_actions"][0]["allowed_actions"]
        job.lease_owner = None
        place = Place(
            name="翠湖公园",
            place_type="PARK",
            external_provider="amap",
            external_poi_id="p",
            latitude=25.03,
            longitude=102.7,
        )
        db.add(place)
        db.flush()
        marker = MapMarkerState(place_id=place.id, visibility="HIDDEN")
        db.add(marker)
        db.commit()
        assert poi_review_contract(db, mention)["candidate_actions"][0]["allowed_actions"] == ["CONFIRM"]
        assert marker.visibility == "HIDDEN"
        db.add(
            PlaceDeletionTombstone(external_provider="amap", external_poi_id="p", former_place_id=place.id)
        )
        db.commit()
        assert poi_review_contract(db, mention)["candidate_actions"][0]["blocked_by"] == ["PLACE_DELETED"]
        mention_id = mention.id
    response = client.get("/api/travel/place-reviews")
    assert response.status_code == 200
    view = next(item for item in response.json() if item["mention_id"] == mention_id)
    assert view["review_contract"]["authority"]["mention_id"] == mention_id


@pytest.mark.parametrize(
    "code,category",
    [
        ("NAME_MATCH_WEAK", "NAME_UNCERTAIN"),
        ("CANDIDATE_GAP_SMALL", "AMBIGUOUS"),
        ("SCENIC_CHILD_ONLY", "OBJECT_CATEGORY"),
        ("QUERY_INCOMPLETE", "INCOMPLETE_CANDIDATES"),
        ("DETAIL_VERIFICATION_FAILED", "DETAIL_MISMATCH"),
        ("NEW_UNKNOWN_CODE", "INSUFFICIENT_EVIDENCE"),
    ],
)
def test_reason_classification_is_code_based(app_and_session, code, category):
    from zhijian.services.poi_review import poi_review_contract

    _, factory = app_and_session
    with factory() as db:
        mention = make_mention(db)
        mention.metadata_json = {
            "reason_codes": [code],
            "reason": "arbitrary display text",
            "poi_candidates": [],
        }
        contract = poi_review_contract(db, mention)
        assert contract["classification"] == category
        assert contract["reason_codes"] == [code]


@pytest.mark.parametrize("detail_matches", [True, False])
def test_isolated_resolver_confirmation_requires_consistent_detail(
    app_and_session, monkeypatch, detail_matches
):
    value = POICandidate("p", "翠湖公园", "昆明市", "云南省", "昆明市", "五华区", 102.7, 25.03, "110000")

    class Provider:
        calls = 0

        def __init__(self, *_args, **_kwargs):
            pass

        def search(self, *_args, **_kwargs):
            self.calls += 1
            return [replace(value)]

        def detail(self, _poi_id):
            self.calls += 1
            return replace(value, city="昆明市" if detail_matches else "大理市")

    monkeypatch.setattr("zhijian.services.video_support.AMapPOIProvider", Provider)
    _, factory = app_and_session
    with factory() as db:
        mention = make_mention(db)
        result = resolve_mentions_with_amap(db, Settings(_env_file=None), [mention], "fixture")
        assert result == ((1, 0) if detail_matches else (0, 1))
        assert mention.raw_name == "翠湖公园"
        if detail_matches:
            assert mention.metadata_json["confirmation_origin"] == "AUTO_STRONG"
            assert mention.metadata_json["poi_id"] == "p"
        else:
            assert mention.metadata_json["reason_codes"] == ["DETAIL_VERIFICATION_FAILED"]


def test_u_mock_contract_has_explicit_versions_and_no_unproved_complete_coverage():
    import json
    from pathlib import Path

    fixture = json.loads((Path(__file__).parent / "fixtures/poi_review_v1.json").read_text())
    assert fixture["evidence_level"] == "SYNTHETIC_MOCK_ONLY"
    for example in fixture["examples"]:
        contract = example["review_contract"]
        assert contract["version"] == "poi-review-v1"
        assert isinstance(contract["authority"]["revision"], int)
        assert contract["search"]["completeness"] in {"UNKNOWN", "PARTIAL"}
        assert contract["evidence"]["snapshot_id"]
        if contract["blocked_by"]:
            assert not contract["allowed_actions"]
            assert all(not item["allowed_actions"] for item in contract["candidate_actions"])
