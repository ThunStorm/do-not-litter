"""Theme membership is evidence, not a global broadcast or a history update."""

from types import SimpleNamespace

import pytest

from zhijian.services.temporal_context import (
    analysis_status,
    application_windows,
    candidate_contexts,
    matches_theme,
    validate_applications,
)
from zhijian.services.travel_timing import matches_window


def sample():
    segments = [
        SimpleNamespace(id=f"s{i}", snapshot_id="snapshot", corrected_text="", text=t)
        for i, t in enumerate(["暑假推荐几个避暑小城。", "第一个推荐甲地。", "接下来推荐乙地。"])
    ]
    contexts = candidate_contexts(segments)
    entity = {
        "entity_id": "e",
        "name": "甲地",
        "subject_role": "PRIMARY",
        "visit_intent": "RECOMMENDED",
        "poi_policy": "RESOLVE",
        "content_unit_id": "u",
        "temporal_applications": [
            {
                "context_id": contexts[0]["context_id"],
                "relation": "INCLUDED",
                "segment_ids": ["s1"],
                "supporting_quote": segments[1].text,
            }
        ],
    }
    units = [
        {
            "content_unit_id": "u",
            "unit_type": "PLACE_GUIDE",
            "anchor_entity_ids": ["e"],
            "segment_ids": ["s1"],
        }
    ]
    return segments, contexts, entity, units


def test_holiday_theme_keeps_semantic_matching_separate_from_months():
    segments, contexts, entity, units = sample()
    apps = validate_applications(entity, units, contexts, segments)
    assert len(apps) == 1
    w = SimpleNamespace(**next(application_windows(apps)))
    assert w.month is None and w.season is None
    assert matches_theme(w, "SUMMER_HOLIDAY") and matches_theme(w, "SUMMER_ESCAPE")
    assert not matches_window(w, month=8)
    assert w.provenance == "THEME_CONTEXT"


@pytest.mark.parametrize(
    "mutation",
    [
        "reference",
        "rejected_intent",
        "unknown_context",
        "wrong_unit",
        "tampered_quote",
        "foreign_snapshot",
        "new_theme",
        "optional",
    ],
)
def test_theme_membership_guards(mutation):
    segments, contexts, entity, units = sample()
    if mutation == "reference":
        entity["subject_role"] = "REFERENCE"
    if mutation == "rejected_intent":
        entity["visit_intent"] = "NOT_RECOMMENDED"
    if mutation == "unknown_context":
        entity["temporal_applications"][0]["context_id"] = "invented"
    if mutation == "wrong_unit":
        units[0]["segment_ids"] = ["s2"]
    if mutation == "tampered_quote":
        entity["temporal_applications"][0]["supporting_quote"] = "甲地8月最好"
    if mutation == "foreign_snapshot":
        segments[1].snapshot_id = "other"
    if mutation == "new_theme":
        contexts.append({**contexts[0], "context_id": "next", "segment_ids": ["s1"], "raw_time_text": "秋天"})
    if mutation == "optional":
        entity["visit_intent"] = "OPTIONAL"
    apps = validate_applications(entity, units, contexts, segments)
    if mutation == "optional":
        assert next(application_windows(apps))["suitability"] == "INFORMATIONAL"
    else:
        assert apps == []


def test_background_without_recommendation_has_no_theme():
    s = SimpleNamespace(id="s", snapshot_id="snap", corrected_text="", text="每年7月15日到8月15日游客最多。")
    assert not candidate_contexts([s])
    assert analysis_status({"temporal_analysis": {"status": "ANALYZED"}}) == "TIME_UNRESOLVED"
    assert analysis_status({}) == "NOT_ANALYZED"


def test_projection_is_fixed_to_note_version_and_shared_by_place_area(client, app_and_session):
    from zhijian.core.config import Settings
    from zhijian.db.models import (
        AINote,
        AINoteVersion,
        Destination,
        GroundedMapArtifact,
        Place,
        Source,
        VideoAsset,
    )
    from zhijian.services.place_experience import effective_windows
    from zhijian.services.temporal_context import projected_theme_windows
    from zhijian.services.video_support import extract_place_mentions, materialize_transcript

    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="fixture://theme")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="旅行")
        db.add(asset)
        db.flush()
        transcript, segs = materialize_transcript(
            db,
            source,
            asset,
            [
                {"text": t, "start_ms": i * 1000, "end_ms": (i + 1) * 1000}
                for i, t in enumerate(["暑假推荐几个避暑小城。", "第一个推荐甲地。", "接下来推荐乙地。"])
            ],
            source_kind="ASR",
        )
        contexts = candidate_contexts(segs)
        entities, units = [], []
        for i, name in enumerate(["甲地", "乙地"], 1):
            entity = {
                "entity_id": f"e{i}",
                "name": name,
                "raw_name": name,
                "subject_role": "PRIMARY",
                "visit_intent": "RECOMMENDED",
                "poi_policy": "RESOLVE" if i == 1 else "AREA_RESOLVE",
                "entity_type": "PLACE" if i == 1 else "AREA",
                "content_unit_id": f"u{i}",
                "segment_ids": [segs[i].id],
                "quote": segs[i].text,
                "temporal_applications": [
                    {
                        "context_id": contexts[0]["context_id"],
                        "relation": "INCLUDED",
                        "segment_ids": [segs[i].id],
                        "supporting_quote": segs[i].text,
                    }
                ],
            }
            unit = {
                "content_unit_id": f"u{i}",
                "unit_type": "PLACE_GUIDE",
                "anchor_entity_ids": [f"e{i}"],
                "segment_ids": [segs[i].id],
            }
            units.append(unit)
            entity["verified_temporal_applications"] = validate_applications(entity, units, contexts, segs)
            entity["temporal_artifact_hash"] = "theme-hash"
            entities.append(entity)
        artifact = GroundedMapArtifact(
            video_asset_id=asset.id,
            transcript_id=transcript.id,
            transcript_version=transcript.version,
            content_hash="text",
            semantic_hash="theme-hash",
            prompt_version="theme",
            supplement_hash="",
            provider="fixture",
            model="fixture",
            semantic_options_json={"temporal_contexts": contexts},
            entities_json=entities,
            content_units_json=units,
        )
        note = AINote(video_asset_id=asset.id)
        place = Place(
            name="甲地",
            canonical_name="甲地",
            place_type="SCENIC_AREA",
            resolution_status="CONFIRMED",
            latitude=30,
            longitude=110,
        )
        area = Destination(name="乙地", canonical_name="乙地")
        db.add_all([artifact, note, place, area])
        db.flush()
        version = AINoteVersion(
            ai_note_id=note.id,
            version=1,
            markdown="",
            transcript_version=transcript.version,
            grounded_map_artifact_id=artifact.id,
        )
        db.add(version)
        db.flush()
        note.current_version_id = version.id
        mentions = extract_place_mentions(
            db, Settings(_env_file=None), asset, version, segs, candidates=entities, content_units=units
        )
        mentions[0].place_id = place.id
        mentions[1].destination_id = area.id
        db.commit()
        pids = [place.id, area.id]
        result = projected_theme_windows(db, pids)
        assert {w.place_id for w in result} == set(pids)
        assert all(w.note_version_id == version.id for w in result)
        assert any(w.provenance == "THEME_CONTEXT" for w in effective_windows(db, [place.id]))
        response = client.get(f"/api/travel/destinations/{area.id}/temporal")
        assert response.status_code == 200
        assert response.json()["visit_windows"][0]["semantics"]["precision"] == "HOLIDAY"
        assert "推荐主题" in response.json()["travel_brief"]["timing"]
        before = db.total_changes if hasattr(db, "total_changes") else len(db.dirty)
        projected_theme_windows(db, pids)
        assert len(db.dirty) == before
        original_meta = mentions[0].metadata_json
        mentions[0].metadata_json = {
            **original_meta,
            "visit_windows": [
                {
                    "month": 8,
                    "suitability": "AVOID",
                    "source_text": "8月中旬以后不推荐",
                    "semantics": {"purpose": "VIEWING"},
                }
            ],
        }
        db.commit()
        assert projected_theme_windows(db, [place.id])[0].suitability == "RECOMMENDED"
        mentions[0].metadata_json = {
            **original_meta,
            "visit_windows": [
                {
                    "month": 8,
                    "suitability": "AVOID",
                    "source_text": "8月中旬以后不推荐",
                    "semantics": {"purpose": "VISIT"},
                }
            ],
        }
        db.commit()
        assert projected_theme_windows(db, [place.id])[0].suitability == "INFORMATIONAL"
        assert projected_theme_windows(db, [area.id])[0].suitability == "RECOMMENDED"
        mentions[0].metadata_json = original_meta
        from zhijian.db.models import PlaceVisitWindow

        manual = PlaceVisitWindow(
            place_id=place.id, provenance="USER", month=12, source_text="人工记录", suitability="RECOMMENDED"
        )
        db.add(manual)
        db.commit()
        assert any(w.id == manual.id for w in effective_windows(db, [place.id]))
        version.grounded_map_artifact_id = None
        db.commit()
        assert not projected_theme_windows(db, pids)


def test_cross_chunk_registry_short_ids_are_lossless_and_unseen_ids_rejected():
    import json

    from zhijian.ai.reliability import AIProviderError
    from zhijian.ai.request_compiler import compile_request

    segments, contexts, entity, units = sample()
    for i, s in enumerate(segments):
        s.ordinal = i
    # This package contains the second unit plus the separately supplied source registry.
    text = f"[segment:s1 1000-2000ms] {segments[1].text}\ncontext_id={contexts[0]['context_id']}\n"
    text += f"[segment:s0 0-1000ms] {segments[0].text}"
    request = compile_request("GROUND_MAP", [{"role": "user", "content": text}], segments, "snapshot")
    payload = {
        "content_units": [{**units[0], "segment_ids": [request.ids["s1"]]}],
        "entities": [
            {
                **entity,
                "segment_ids": [request.ids["s1"]],
                "temporal_applications": [
                    {**entity["temporal_applications"][0], "segment_ids": [request.ids["s1"]]}
                ],
            }
        ],
        "claims": [],
        "relations": [],
    }
    restored = json.loads(request.decode(json.dumps(payload)))
    application = restored["entities"][0]["temporal_applications"][0]
    assert application["context_id"] == contexts[0]["context_id"]
    assert application["segment_ids"] == ["s1"]
    assert restored["entities"][0]["content_unit_id"] == restored["content_units"][0]["content_unit_id"]
    payload["entities"][0]["temporal_applications"][0]["segment_ids"] = [request.ids["s2"]]
    with pytest.raises(AIProviderError):
        request.decode(json.dumps(payload))


def test_chunk_registry_has_only_active_theme_and_current_switches():
    from zhijian.services.temporal_context import contexts_for_chunk

    segments, contexts, _, _ = sample()
    first = contexts[0]
    second = {**first, "context_id": "fall", "segment_ids": ["s1"]}
    assert contexts_for_chunk([first, second], segments, [segments[2]]) == [second]
    assert contexts_for_chunk([first, second], segments, segments[:2]) == [first, second]


@pytest.mark.parametrize("month", ["13月", "十三月", "0月"])
def test_invalid_theme_month_does_not_become_a_valid_month(month):
    s = SimpleNamespace(id="s", snapshot_id="snapshot", corrected_text="", text=f"{month}推荐几个小城。")
    assert candidate_contexts([s]) == []


def test_saved_opening_does_not_project_peak_travel_dates():
    import json
    from pathlib import Path

    from zhijian.services.travel_timing import window_label

    d = json.loads((Path(__file__).parent / "fixtures/video_temporal_context.json").read_text())
    contexts = candidate_contexts([SimpleNamespace(**s) for s in d["opening_segments"]])
    assert [c["raw_time_text"] for c in contexts] == ["暑假"]
    app = {"context": contexts[0], "relation": "INCLUDED"}
    w = SimpleNamespace(**next(application_windows([app])))
    assert w.month is None and window_label(w) == "暑假"
    assert not matches_window(w, month=8)


def test_neutral_overall_intent_requires_explicit_list_entry_and_does_not_change_intent():
    segments, contexts, entity, units = sample()
    entity["visit_intent"] = "NEUTRAL"
    segments[1].text = "甲地风景不错。"
    entity["temporal_applications"][0]["supporting_quote"] = segments[1].text
    assert validate_applications(entity, units, contexts, segments) == []
    segments[1].text = "接下来推荐甲地。"
    entity["temporal_applications"][0]["supporting_quote"] = segments[1].text
    assert validate_applications(entity, units, contexts, segments)
    assert entity["visit_intent"] == "NEUTRAL"


def test_explicit_source_list_child_recovery_does_not_upgrade_overall_intent():
    from zhijian.services.temporal_context import recover_source_membership

    texts = [
        "暑假推荐几个避暑小城。",
        "接下来甲地。",
        "还有甲草原，而且这个草原",
        "是白牦牛牧区所以一定要过来打卡当然还有别的地方。",
    ]
    segs = [
        SimpleNamespace(id=f"s{i}", snapshot_id="snapshot", text=t, corrected_text="")
        for i, t in enumerate(texts)
    ]
    contexts = candidate_contexts(segs)
    units = [
        {
            "content_unit_id": "u",
            "unit_type": "AREA_GUIDE",
            "anchor_entity_ids": ["parent"],
            "segment_ids": ["s1", "s3"],
        }
    ]
    parent = {
        "entity_id": "parent",
        "name": "甲地",
        "raw_name": "甲地",
        "content_unit_id": "u",
        "segment_ids": ["s1"],
        "subject_role": "PRIMARY",
        "visit_intent": "NEUTRAL",
        "poi_policy": "AREA_RESOLVE",
        "temporal_applications": [],
    }
    child = {
        "entity_id": "child",
        "name": "甲草原",
        "raw_name": "甲草原",
        "content_unit_id": "u",
        "segment_ids": ["s2"],
        "subject_role": "SECONDARY",
        "visit_intent": "NEUTRAL",
        "poi_policy": "RESOLVE",
        "temporal_applications": [],
    }
    recover_source_membership([parent, child], units, contexts, segs)
    apps = validate_applications(child, units, contexts, segs)
    assert len(apps) == 1 and apps[0]["derivation"] == "EXPLICIT_SOURCE_LIST_CHILD"
    assert apps[0]["segment_ids"] == ["s2", "s3"] and child["visit_intent"] == "NEUTRAL"
    child["subject_role"] = "REFERENCE"
    assert validate_applications(child, units, contexts, segs) == []


def test_unassigned_grass_restriction_is_retained_without_city_projection():
    from zhijian.services.temporal_context import unresolved_temporal_evidence

    segs = [
        SimpleNamespace(id="s1", snapshot_id="snapshot", text="不过八月中旬", corrected_text=""),
        SimpleNamespace(id="s2", snapshot_id="snapshot", text="之后就不再推荐去草原了。", corrected_text=""),
    ]
    evidence = unresolved_temporal_evidence(segs, [])
    assert len(evidence) == 1 and evidence[0]["segment_ids"] == ["s1", "s2"]
    assert evidence[0]["scope"] == "UNRESOLVED_LOCAL_SUBJECT" and evidence[0]["status"] == "NEEDS_REVIEW"
    assert "entity_id" not in evidence[0] and "month" not in evidence[0]


def test_recommendation_theme_is_not_promoted_to_best_viewing_period():
    from zhijian.services.travel_recommendations import visit_window_summary

    segments, contexts, entity, units = sample()
    apps = validate_applications(entity, units, contexts, segments)
    data = next(application_windows(apps))
    ids = data.pop("segment_ids")
    w = SimpleNamespace(**data, source_id="source", segment_ids_json=ids)
    assert w.period_type == "OTHER"
    assert visit_window_summary([w])["state"] == "GOOD"


@pytest.mark.parametrize(
    "local,theme,expected",
    [
        ({"season": "WINTER"}, {"month": 8}, False),
        ({"season": "SUMMER"}, {"month": 8}, True),
        ({"season": "WINTER"}, {"month": 1}, True),
        ({"source_text": "8月1日到8月10日"}, {"source_text": "8月20日到8月31日"}, False),
        ({"source_text": "12月20日到1月10日"}, {"month": 1}, True),
    ],
)
def test_theme_conflict_requires_overlapping_calendar(local, theme, expected):
    from zhijian.services.temporal_context import temporal_windows_overlap

    assert temporal_windows_overlap(local, theme) == expected
