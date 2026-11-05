import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from zhijian.services.note_quality import quality_summary, safe_note_prose, source_gaps
from zhijian.services.note_structure import organize_sections, structured_overview
from zhijian.services.recommendation_intent import assess
from zhijian.services.semantic_identity import join_boundary_entities, topic_chunks
from zhijian.services.temporal_context import candidate_contexts
from zhijian.services.video_support import _ground_section

FIXTURE = Path(__file__).parent / "fixtures/travel_pipeline/december_reverse_bv1hrxe6yebq"


def baseline():
    data = json.loads((FIXTURE / "baseline.json").read_text())
    segments = [SimpleNamespace(**{**s, "corrected_text": s["text"]}) for s in data["segments"]]
    return data, segments


def test_golden_original_clauses_are_traceable_and_not_generated():
    data, _ = baseline()
    texts = {s["id"]: s["text"] for s in data["segments"]}
    facts = json.loads((FIXTURE / "golden_facts.json").read_text())
    assert len(facts) == 24
    for fact in facts:
        assert fact["quote"] in "".join(texts[s] for s in fact["segment_ids"])


def test_topic_requests_preserve_every_segment_and_shared_transition():
    _, segments = baseline()
    chunks = topic_chunks(segments, lambda group: [group])
    assert len(chunks) == 5
    assert max(map(len, chunks)) <= 16
    assert {s.id for c in chunks for s in c} == {s.id for s in segments}
    assert all(a[-1].id == b[0].id for a, b in zip(chunks, chunks[1:], strict=False))


def test_rejected_anchor_requires_an_exact_shared_named_introduction():
    segments = [
        SimpleNamespace(id="intro", corrected_text="", text="接下来西藏拉萨十二月份肯定是首选"),
        SimpleNamespace(id="details", corrected_text="", text="冬天景区大多免门票"),
    ]
    entity = {"entity_id": "known", "raw_name": "西藏拉萨", "canonical_hint": "西藏拉萨",
              "subject_role": "PRIMARY", "entity_type": "AREA", "quote": segments[0].text,
              "content_unit_id": "intro-unit", "segment_ids": ["intro"]}
    left = {"content_unit_id": "intro-unit", "unit_type": "AREA_GUIDE",
            "anchor_entity_ids": ["known"], "segment_ids": ["intro"]}
    right = {"content_unit_id": "main-unit", "unit_type": "MIXED", "unit_type_omitted": True,
             "topic": "拉萨十二月份反向旅游", "anchor_entity_ids": ["rejected"],
             "segment_ids": ["intro", "details"]}
    claims = [{"claim_id": "fact", "subject_entity_ids": ["rejected"], "segment_ids": ["details"]}]
    entities, units, result, _ = join_boundary_entities([entity], [left, right], claims, [], segments)
    assert entities[0]["quote"] == segments[0].text
    assert result[0]["subject_entity_ids"] == ["known"]
    assert units[1]["unit_type"] == "AREA_GUIDE"
    _, units, result, _ = join_boundary_entities(
        [entity], [left, {**right, "topic": "另一城市旅游"}], claims, [], segments
    )
    assert units[1]["unit_type"] == "MIXED"
    assert result[0]["subject_entity_ids"] == ["rejected"]


def test_boundary_lhasa_identity_retains_both_sources_and_original_ids():
    data, segments = baseline()
    semantic = data["semantic_map"]
    entities, units, claims, _ = join_boundary_entities(
        semantic["entities"], semantic["content_units"], semantic["claims"], semantic["relations"], segments
    )
    lhasa = [e for e in entities if e["canonical_hint"] == "拉萨"]
    assert len(lhasa) == 1
    assert len(lhasa[0]["identity_derivation"]["entity_ids"]) == 2
    assert len(lhasa[0]["segment_ids"]) == 2
    entity_ids = {e["entity_id"] for e in entities}
    original_ids = {e["entity_id"] for e in semantic["entities"]}
    unresolved = {sid for c in semantic["claims"] for sid in c["subject_entity_ids"]} - original_ids
    assert all(set(c["subject_entity_ids"]) <= entity_ids | unresolved for c in claims)
    assert all(set(u["anchor_entity_ids"]) <= entity_ids for u in units)
    reverse, *_ = join_boundary_entities(
        semantic["entities"][::-1], semantic["content_units"][::-1], semantic["claims"],
        semantic["relations"], segments,
    )
    assert [e for e in reverse if e["canonical_hint"] == "拉萨"] == lhasa


@pytest.mark.parametrize("mutation", ["region", "transition", "finished", "nonadjacent"])
def test_boundary_identity_rejects_ambiguous_or_unrelated_names(mutation):
    data, segments = baseline()
    semantic = copy.deepcopy(data["semantic_map"])
    entities = [e for e in semantic["entities"] if e["canonical_hint"] == "拉萨"]
    if mutation == "region":
        entities[0]["city_hint"], entities[1]["city_hint"] = "甲市", "乙市"
    elif mutation == "transition":
        segments[38].corrected_text = "接下来另一个同名目的地"
    elif mutation == "finished":
        segments[37].corrected_text += "。"
    else:
        semantic["content_units"] = [
            {**u, "segment_ids": u["segment_ids"][1:]} if u["topic"].startswith("拉萨") else u
            for u in semantic["content_units"]
        ]
    result, *_ = join_boundary_entities(entities, semantic["content_units"], [], [], segments)
    assert len(result) == 2


def test_explicit_unit_hierarchy_merges_area_and_children_without_losing_anchors():
    data, _ = baseline()
    mentions = [SimpleNamespace(**m) for m in data["mentions"]]
    result = organize_sections(
        data["sections"], mentions, content_units=data["semantic_map"]["content_units"]
    )
    assert len([s for s in result if s["heading"] == "广西河池"]) == 1
    river = next(s for s in result if s["heading"] == "广西河池")
    original = [s for s in data["sections"] if "河池" in s["heading"] or s["heading"] == "三门海"]
    assert {s["id"] for s in original} <= set(river["source_section_ids"])
    assert all(sid in river["segment_ids"] for s in original for sid in s["segment_ids"])
    assert any(s["heading"] == "拉萨" for s in result)
    # Old data has two identities; read organization must not mutate those identities.
    assert len([m for m in mentions if m.name == "拉萨"]) == 2


@pytest.mark.parametrize("quote", ["A最适合反向旅游的目的地", "A适合喜欢清净的人", "A肯定是首选"])
def test_positive_expression_requires_independent_grounding(quote):
    statement = {
        "statement_id": "s1", "intent": "RECOMMENDED", "scope": "PLACE_OVERALL",
        "subject_entity_id": "a", "speaker": "AUTHOR", "quote": quote, "segment_ids": ["s"],
    }
    entity = {"entity_id": "a", "name": "A", "visit_intent": "RECOMMENDED",
              "recommendation_evidence": {"statements": [statement]}}
    assert assess(entity, {"s": quote})["status"] == "RECOMMENDED"
    assert assess(entity, {"s": "另一句话"})["status"] == "UNKNOWN"


@pytest.mark.parametrize("quote", ["A不适合旅游", "A不是首选", "A不太适合喜欢清净的人"])
def test_positive_words_inside_negation_do_not_verify_recommendation(quote):
    entity = {"entity_id": "a", "name": "A", "visit_intent": "RECOMMENDED", "recommendation_evidence": {
        "statements": [{"statement_id": "r", "intent": "RECOMMENDED", "scope": "PLACE_OVERALL",
                        "subject_entity_id": "a", "speaker": "AUTHOR", "quote": quote, "segment_ids": ["s"]}]
    }}
    assert assess(entity, {"s": quote})["status"] == "UNKNOWN"


def test_source_scan_reports_omitted_risks_without_creating_claims():
    data, segments = baseline()
    semantic = data["semantic_map"]
    before = copy.deepcopy(semantic)
    gaps = source_gaps(segments, semantic["claims"], semantic["content_units"])
    assert any("灌水" in g["supporting_quote"] for g in gaps)
    assert any("没有房" in g["supporting_quote"] for g in gaps)
    assert all(g["reason"] == "POSSIBLE_SOURCE_OMISSION" for g in gaps)
    assert semantic == before


def test_split_december_does_not_create_a_february_theme_or_verified_attribution():
    _, segments = baseline()
    for segment in segments:
        segment.snapshot_id = "snapshot"
    contexts = candidate_contexts(segments)
    months = {c["raw_time_text"] for c in contexts}
    assert "十二月份" in months
    assert "二月份" not in months
    assert safe_note_prose("十二月份人少", ["十二月份还有哪块人少景美"], {"二"})
    assert not safe_note_prose("二月份反向旅游主题", ["十二月份还有哪块人少景美"], {"二"})
    assert not safe_note_prose("被国家地理评为最美天坑", ["被国家地理成为中国最美的天这个"], set())


def test_quality_is_evidence_coverage_not_semantic_pass_or_latest_job():
    report = quality_summary("old-version", [{
        "id": "chapter", "place_mention_ids": [], "segment_ids": ["s"],
        "evidence_quotes": ["可能没房"],
    }], [{"segment_ids": ["s"], "supporting_quotes": ["可能没房"]}], [])
    assert report["note_version_id"] == "old-version"
    assert report["evidence_represented_count"] == 1
    assert report["status"] == "UNKNOWN"
    assert report["generation_mode"] == "UNKNOWN"
    assert report["summarized_fact_count"] is None


def test_overview_does_not_repeat_review_placeholders():
    result = structured_overview([
        {"heading": "河池", "section_kind": "PLACE_GUIDE", "thesis": "作者意见或归纳待核对"},
        {"heading": "玉溪", "section_kind": "PLACE_GUIDE", "thesis": "待归纳原文"},
    ], "旧占位摘要")
    assert "河池、玉溪" in result
    assert "作者意见或归纳待核对" not in result


def test_merged_chapter_does_not_truncate_evidence_after_eight_quotes():
    segments = [SimpleNamespace(id=f"s{i}", text=f"事实{i}。", corrected_text="") for i in range(12)]
    item = {"segment_ids": [s.id for s in segments], "supporting_quotes": [s.text for s in segments],
            "section_kind": "SUPPLEMENTAL"}
    result = _ground_section(item, segments, [])
    assert len(result["supporting_quotes"]) == 12
