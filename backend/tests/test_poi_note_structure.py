import json
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from zhijian.ai.reliability import AIProviderError
from zhijian.core.config import Settings
from zhijian.db.models import (
    AINote,
    AINoteSection,
    AINoteVersion,
    GroundedMapArtifact,
    MapMarkerState,
    PlaceMention,
    Source,
    VideoAsset,
)
from zhijian.providers.llm import LLMResult
from zhijian.services.note_structure import organize_sections
from zhijian.services.video_support import (
    _ground_map_facts,
    _ground_section,
    generate_note,
    materialize_transcript,
)


def note_artifact(db, asset, transcript, facts):
    artifact = GroundedMapArtifact(
        video_asset_id=asset.id, transcript_id=transcript.id, transcript_version=transcript.version,
        content_hash="fixture", semantic_hash="fixture", prompt_version="fixture", supplement_hash="",
        provider="fixture", model="fixture", claims_json=[], facts_json=facts, warnings_json=[],
    )
    db.add(artifact)
    db.flush()
    return artifact


def sample(db):
    source = Source(source_type="URL", locator="fixture://places-note", title="地点论述")
    db.add(source)
    db.flush()
    asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="甲乙景点比较")
    db.add(asset)
    db.flush()
    transcript, segments = materialize_transcript(
        db,
        source,
        asset,
        [
            {"text": "甲园门票20元", "start_ms": 0, "end_ms": 1000},
            {"text": "乙馆周一闭馆", "start_ms": 1000, "end_ms": 2000},
            {"text": "甲园日落适合拍照", "start_ms": 2000, "end_ms": 3000},
        ],
        source_kind="FIXTURE",
    )
    mentions = [
        PlaceMention(
            video_asset_id=asset.id,
            name=name,
            place_type="PARK",
            segment_ids_json=[segments[i].id],
            quote=segments[i].text,
            poi_policy="RESOLVE",
            metadata_json={"semantic": {"entity_id": entity}},
        )
        for i, name, entity in [(0, "甲园", "e1"), (1, "乙馆", "e2")]
    ]
    db.add_all(mentions)
    db.flush()
    facts = [
        {
            "summary": seg.text,
            "supporting_quotes": [seg.text],
            "segment_ids": [seg.id],
            "subject_entity_ids": ["e1" if i != 1 else "e2"],
        }
        for i, seg in enumerate(segments)
    ]
    return asset, transcript, segments, mentions, facts


def test_confirmed_poi_is_visible_immediately_without_map_read_backfill(client, app_and_session):
    _, factory = app_and_session
    with factory() as db:
        asset, _, _, mentions, _ = sample(db)
        mention = mentions[0]
        mention.metadata_json = {
            "poi_candidates": [
                {"provider_id": "poi-local", "name": "甲园", "longitude": 102.7, "latitude": 25.05}
            ]
        }
        db.commit()
        mid = mention.id
    result = client.post(
        f"/api/travel/place-mentions/{mid}/confirm",
        json={"provider": "AMAP", "poi_id": "poi-local", "expected_revision": 0},
    )
    assert result.status_code == 200
    pid = result.json()["place_id"]
    assert any(m["id"] == pid for m in client.get("/api/travel/map").json()["markers"])
    with factory() as db:
        state = db.scalar(select(MapMarkerState).where(MapMarkerState.place_id == pid))
        assert state is not None and state.visibility == "VISIBLE"
    client.post(f"/api/travel/places/{pid}/marker/hide")
    assert (
        client.post(
            f"/api/travel/place-mentions/{mid}/confirm",
            json={"provider": "AMAP", "poi_id": "poi-local", "expected_revision": 1},
        ).status_code
        == 200
    )
    assert not any(m["id"] == pid for m in client.get("/api/travel/map").json()["markers"])


def test_later_explicit_subject_keeps_place_identity_and_does_not_broadcast(app_and_session):
    _, factory = app_and_session
    with factory() as db:
        _, _, segments, mentions, facts = sample(db)
        grounded = _ground_map_facts(facts, segments, mentions)
        assert grounded[2]["place_mention_ids"] == [mentions[0].id]
        unknown = _ground_map_facts([{**facts[2], "subject_entity_ids": ["unknown"]}], segments, mentions)
        assert unknown[0]["place_mention_ids"] == []
        assert (
            _ground_section(
                {"segment_ids": [segments[0].id, "seg-unknown"], "supporting_quotes": [segments[0].text]},
                segments,
                mentions,
            )
            is None
        )
        assert (
            _ground_section(
                {"segment_ids": [segments[0].id], "supporting_quotes": ["虚构原句"]}, segments, mentions
            )
            is None
        )


def test_global_grouping_keeps_comparison_and_disjoint_source_anchors():
    mention = SimpleNamespace(
        id="m1",
        place_id=None,
        name="甲园",
        metadata_json={},
        extraction_status="EXTRACTED",
        poi_policy="RESOLVE",
    )
    sections = [
        {
            "id": "a",
            "heading": "甲园费用",
            "section_kind": "PLACE_GUIDE",
            "thesis": "门票20元。",
            "body_markdown": "门票20元。",
            "place_mention_ids": ["m1"],
            "segment_ids": ["s1"],
            "start_ms": 0,
            "end_ms": 1000,
        },
        {
            "id": "b",
            "heading": "甲乙对比",
            "section_kind": "CATEGORY_COMPARE",
            "body_markdown": "两地价格不同。",
            "place_mention_ids": ["m1"],
            "segment_ids": ["s2"],
            "start_ms": 1000,
            "end_ms": 2000,
        },
        {
            "id": "c",
            "heading": "甲园拍摄",
            "section_kind": "PLACE_GUIDE",
            "body_markdown": "日落适合拍照。",
            "place_mention_ids": ["m1"],
            "segment_ids": ["s3"],
            "start_ms": 2000,
            "end_ms": 3000,
        },
    ]
    grouped = organize_sections(sections, [mention])
    assert [s["heading"] for s in grouped] == ["甲园", "甲乙对比"]
    assert grouped[0]["source_section_ids"] == ["a", "c"]
    assert grouped[0]["segment_ids"] == ["s1", "s3"]
    assert len(grouped[0]["source_ranges"]) == 2
    assert "门票20元" in grouped[0]["body_markdown"] and "日落适合拍照" in grouped[0]["body_markdown"]


def test_historical_read_grouping_keeps_stored_version_untouched(client, app_and_session):
    _, factory = app_and_session
    with factory() as db:
        asset, transcript, segments, mentions, facts = sample(db)
        note = AINote(video_asset_id=asset.id, status="COMPLETED")
        db.add(note)
        db.flush()
        version = AINoteVersion(
            ai_note_id=note.id,
            version=1,
            markdown="原始Markdown",
            overview="原始概览",
            transcript_version=transcript.version,
            map_facts_json=_ground_map_facts(facts, segments, mentions),
        )
        db.add(version)
        db.flush()
        note.current_version_id = version.id
        for i in [0, 2]:
            db.add(
                AINoteSection(
                    ai_note_version_id=version.id,
                    ordinal=i,
                    heading=f"甲园要点{i}",
                    section_kind="PLACE_GUIDE",
                    thesis=segments[i].text,
                    body_markdown=segments[i].text,
                    segment_ids_json=[segments[i].id],
                    place_mention_ids_json=[mentions[0].id],
                    evidence_quotes_json=[segments[i].text],
                    start_ms=i * 1000,
                    end_ms=(i + 1) * 1000,
                )
            )
        db.commit()
        nid = note.id
        vid = version.id
    view = client.get(f"/api/video-notes/{nid}").json()
    assert len(view["sections"]) == 2 and len(view["reading_sections"]) == 1
    assert view["reading_sections"][0]["heading"] == "甲园"
    assert view["markdown"] == "原始Markdown"
    with factory() as db:
        assert db.get(AINoteVersion, vid).overview == "原始概览"
        assert (
            len(db.scalars(select(AINoteSection).where(AINoteSection.ai_note_version_id == vid)).all()) == 2
        )


def test_new_generation_merges_across_packs_and_audits_omitted_facts(app_and_session, monkeypatch):
    import zhijian.services.video_support as support

    _, factory = app_and_session
    with factory() as db:
        asset, transcript, segments, mentions, facts = sample(db)
        artifact = note_artifact(db, asset, transcript, facts)
        provider = SimpleNamespace(request_options=SimpleNamespace(max_output_tokens=4096))
        monkeypatch.setattr(support, "provider_for_role", lambda *a: (provider, "fixture", "fixture"))
        payload = {
            "overview": "本包的时间顺序总结",
            "sections": [
                {
                    "heading": "甲园费用",
                    "unit_type": "PLACE_GUIDE",
                    "thesis": "门票20元。",
                    "summary": "门票20元。",
                    "segment_ids": [segments[0].id],
                    "place_mention_ids": [mentions[0].id],
                    "supporting_quotes": [segments[0].text],
                }
            ],
        }
        monkeypatch.setattr(
            support,
            "_cached_stage_json",
            lambda *a, **k: LLMResult(json.dumps(payload, ensure_ascii=False), "fixture", "fixture", {}),
        )
        version = generate_note(
            db,
            Settings(_env_file=None),
            asset,
            transcript,
            segments,
            mentions=mentions,
            grounded_map=artifact,
        )
        sections = db.scalars(
            select(AINoteSection).where(AINoteSection.ai_note_version_id == version.id)
        ).all()
        assert len([s for s in sections if s.heading == "甲园"]) == 1
        assert any("未被模型章节完整覆盖" in w for w in version.warnings_json)
        assert "本包" not in version.overview
        assert set(sid for s in sections for sid in s.segment_ids_json) == {s.id for s in segments}


def test_valid_global_id_from_another_package_is_rejected(app_and_session, monkeypatch):
    import zhijian.services.video_support as support

    _, factory = app_and_session
    with factory() as db:
        asset, transcript, segments, mentions, facts = sample(db)
        provider = SimpleNamespace(request_options=SimpleNamespace(max_output_tokens=640))
        monkeypatch.setattr(support, "provider_for_role", lambda *a: (provider, "fixture", "fixture"))
        payload = {
            "sections": [
                {
                    "unit_type": "PLACE_GUIDE",
                    "heading": "甲园",
                    "segment_ids": [segments[2].id],
                    "place_mention_ids": [mentions[0].id],
                    "supporting_quotes": [segments[2].text],
                }
            ]
        }
        monkeypatch.setattr(
            support,
            "_cached_stage_json",
            lambda *a, **k: LLMResult(json.dumps(payload, ensure_ascii=False), "fixture", "fixture", {}),
        )
        with pytest.raises(AIProviderError, match="来源与地点归属校验"):
            generate_note(
                db,
                Settings(_env_file=None),
                asset,
                transcript,
                segments,
                mentions=mentions,
                grounded_map=note_artifact(db, asset, transcript, facts),
            )


def test_legacy_heading_recovery_requires_place_window_and_exact_quote():
    a = SimpleNamespace(
        id="a",
        place_id=None,
        name="甲园",
        metadata_json={},
        extraction_status="EXTRACTED",
        poi_policy="RESOLVE",
    )
    b = SimpleNamespace(
        id="b",
        place_id=None,
        name="乙馆",
        metadata_json={},
        extraction_status="EXTRACTED",
        poi_policy="RESOLVE",
    )
    segments = [
        SimpleNamespace(id=f"s{i}", corrected_text=text, text=text)
        for i, text in enumerate(["甲园门票20元", "坐公交到这儿", "乙馆周一闭馆", "不能确认是谁的交通"])
    ]

    def section(index, heading, mids):
        return {
            "id": str(index),
            "heading": heading,
            "section_kind": "PLACE_GUIDE",
            "segment_ids": [f"s{index}"],
            "place_mention_ids": mids,
            "evidence_quotes": [segments[index].text],
            "body_markdown": segments[index].text,
        }

    parts = [
        section(0, "甲园介绍", ["a"]),
        section(1, "甲园交通", []),
        section(2, "乙馆介绍", ["b"]),
        section(3, "甲园交通待核实", []),
    ]
    grouped = organize_sections(parts, [a, b], segments=segments, legacy=True)
    assert grouped[0]["source_section_ids"] == ["0", "1"]
    assert parts[1]["place_mention_ids"] == []  # Read grouping does not rewrite historical attribution.
    parts[1]["evidence_quotes"] = ["不存在的原句"]
    assert organize_sections(parts, [a, b], segments=segments, legacy=True)[0]["source_section_ids"] == ["0"]
