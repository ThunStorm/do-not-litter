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
    entity = {
        "entity_id": "known",
        "raw_name": "西藏拉萨",
        "canonical_hint": "西藏拉萨",
        "subject_role": "PRIMARY",
        "entity_type": "AREA",
        "quote": segments[0].text,
        "content_unit_id": "intro-unit",
        "segment_ids": ["intro"],
    }
    left = {
        "content_unit_id": "intro-unit",
        "unit_type": "AREA_GUIDE",
        "anchor_entity_ids": ["known"],
        "segment_ids": ["intro"],
    }
    right = {
        "content_unit_id": "main-unit",
        "unit_type": "MIXED",
        "unit_type_omitted": True,
        "topic": "拉萨十二月份反向旅游",
        "anchor_entity_ids": ["rejected"],
        "segment_ids": ["intro", "details"],
    }
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
        semantic["entities"][::-1],
        semantic["content_units"][::-1],
        semantic["claims"],
        semantic["relations"],
        segments,
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
        "statement_id": "s1",
        "intent": "RECOMMENDED",
        "scope": "PLACE_OVERALL",
        "subject_entity_id": "a",
        "speaker": "AUTHOR",
        "quote": quote,
        "segment_ids": ["s"],
    }
    entity = {
        "entity_id": "a",
        "name": "A",
        "visit_intent": "RECOMMENDED",
        "recommendation_evidence": {"statements": [statement]},
    }
    assert assess(entity, {"s": quote})["status"] == "RECOMMENDED"
    assert assess(entity, {"s": "另一句话"})["status"] == "UNKNOWN"


@pytest.mark.parametrize("quote", ["A不适合旅游", "A不是首选", "A不太适合喜欢清净的人"])
def test_positive_words_inside_negation_do_not_verify_recommendation(quote):
    entity = {
        "entity_id": "a",
        "name": "A",
        "visit_intent": "RECOMMENDED",
        "recommendation_evidence": {
            "statements": [
                {
                    "statement_id": "r",
                    "intent": "RECOMMENDED",
                    "scope": "PLACE_OVERALL",
                    "subject_entity_id": "a",
                    "speaker": "AUTHOR",
                    "quote": quote,
                    "segment_ids": ["s"],
                }
            ]
        },
    }
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
    report = quality_summary(
        "old-version",
        [
            {
                "id": "chapter",
                "place_mention_ids": [],
                "segment_ids": ["s"],
                "evidence_quotes": ["可能没房"],
            }
        ],
        [{"segment_ids": ["s"], "supporting_quotes": ["可能没房"]}],
        [],
    )
    assert report["note_version_id"] == "old-version"
    assert report["evidence_represented_count"] == 1
    assert report["status"] == "UNKNOWN"
    assert report["generation_mode"] == "UNKNOWN"
    assert report["summarized_fact_count"] is None


def test_overview_does_not_repeat_review_placeholders():
    result = structured_overview(
        [
            {"heading": "河池", "section_kind": "PLACE_GUIDE", "thesis": "作者意见或归纳待核对"},
            {"heading": "玉溪", "section_kind": "PLACE_GUIDE", "thesis": "待归纳原文"},
        ],
        "旧占位摘要",
    )
    assert "河池、玉溪" in result
    assert "作者意见或归纳待核对" not in result


def test_merged_chapter_does_not_truncate_evidence_after_eight_quotes():
    segments = [SimpleNamespace(id=f"s{i}", text=f"事实{i}。", corrected_text="") for i in range(12)]
    item = {
        "segment_ids": [s.id for s in segments],
        "supporting_quotes": [s.text for s in segments],
        "section_kind": "SUPPLEMENTAL",
    }
    result = _ground_section(item, segments, [])
    assert len(result["supporting_quotes"]) == 12


@pytest.mark.parametrize("right_kind", ["PLACE_GUIDE", "MULTI_PLACE_LIST"])
def test_shared_named_scenic_introduction_has_one_identity_and_keeps_evidence(right_kind):
    text = "第三个，四川海螺沟。一个冰瀑加神山的跨年之旅，肯定是"
    segments = [
        SimpleNamespace(id="intro", text=text, corrected_text=text),
        SimpleNamespace(id="tail", text="超值了，还能泡温泉。", corrected_text=""),
    ]
    base = {
        "raw_name": "四川海螺沟",
        "name": "海螺沟",
        "entity_type": "PLACE",
        "place_type": "SCENIC_AREA",
        "subject_role": "PRIMARY",
    }
    entities = [
        {**base, "entity_id": "a", "content_unit_id": "left", "quote": text, "segment_ids": ["intro"]},
        {
            **base,
            "entity_id": "b",
            "content_unit_id": "right",
            "quote": text + "超值了",
            "segment_ids": ["intro", "tail"],
        },
    ]
    units = [
        {
            "content_unit_id": "left",
            "unit_type": "PLACE_GUIDE",
            "anchor_entity_ids": ["a"],
            "segment_ids": ["intro"],
        },
        {
            "content_unit_id": "right",
            "unit_type": right_kind,
            "anchor_entity_ids": ["b"],
            "segment_ids": ["intro", "tail"],
        },
    ]
    claims = [{"claim_id": "c", "subject_entity_ids": ["a"], "segment_ids": ["intro"]}]
    result, joined_units, joined_claims, _ = join_boundary_entities(entities, units, claims, [], segments)
    assert len(result) == 1
    assert result[0]["segment_ids"] == ["intro", "tail"]
    assert result[0]["identity_derivation"]["version"] == "adjacent-scenic-introduction-v1"
    assert joined_claims[0]["subject_entity_ids"] == [result[0]["entity_id"]]
    assert all(u["anchor_entity_ids"] == [result[0]["entity_id"]] for u in joined_units)
    assert joined_units[1]["unit_type"] == right_kind  # comparison/list identity is retained
    # A different named introduction is not the same identity even with an equal canonical hint.
    entities[1] = {**entities[1], "raw_name": "辽宁海螺沟", "quote": "辽宁海螺沟"}
    assert len(join_boundary_entities(entities, units, claims, [], segments)[0]) == 2


def test_reduce_requires_every_fact_quote_with_its_own_source_and_subject():
    from zhijian.ai.note_evidence import validate_pack_coverage
    from zhijian.ai.reliability import AIProviderError

    pack = [
        {"segment_ids": ["s1"], "place_mention_ids": ["a"], "supporting_quotes": ["船次限流六艘"]},
        {"segment_ids": ["s2"], "place_mention_ids": ["b"], "supporting_quotes": ["高反人群劝退"]},
    ]
    first = {"segment_ids": ["s1"], "place_mention_ids": ["a"], "supporting_quotes": ["船次限流六艘"]}
    with pytest.raises(AIProviderError, match="完整逐字引文"):
        validate_pack_coverage({"sections": [first]}, pack)
    wrong = {"segment_ids": ["s2"], "place_mention_ids": ["a"], "supporting_quotes": ["高反人群劝退"]}
    with pytest.raises(AIProviderError):
        validate_pack_coverage({"sections": [first, wrong]}, pack)
    second = {**wrong, "place_mention_ids": ["b"]}
    validate_pack_coverage({"sections": [first, second]}, pack)
    # Combining exact quotes in one longer quotation is allowed; unrelated quotes are not coverage.
    validate_pack_coverage(
        {
            "sections": [
                {
                    "segment_ids": ["s1", "s2"],
                    "place_mention_ids": ["a", "b"],
                    "supporting_quotes": ["船次限流六艘；高反人群劝退"],
                }
            ]
        },
        pack,
    )


def test_visible_source_context_closes_coverage_gap_but_pending_fallback_does_not():
    from zhijian.services.note_quality import source_gaps

    segment = SimpleNamespace(id="s", text="元旦跨年最适合去哪里", corrected_text="")
    section = {"section_kind": "THEME", "segment_ids": ["s"], "evidence_quotes": [segment.text]}
    assert not source_gaps([segment], [], [], sections=[section])
    assert not source_gaps([segment], [], [], sections=[{**section, "supporting_quotes": []}])
    assert source_gaps([segment], [], [], sections=[{**section, "section_kind": "SOURCE_REVIEW"}])
    assert source_gaps([segment], [], [], sections=[{**section, "segment_ids": ["wrong"]}])


def test_missing_child_opinion_stays_visible_as_candidate_review_not_a_body_error():
    from zhijian.services.note_quality import quality_summary

    opinion = {
        "schema_version": "recommendation-v1",
        "assessment_status": "NEEDS_REVIEW",
        "status": "UNKNOWN",
        "reason_codes": ["MISSING_OVERALL_EVIDENCE"],
        "statements": [],
    }
    mention = SimpleNamespace(
        id="child",
        subject_role="SECONDARY",
        visit_intent="RECOMMENDED",
        metadata_json={"recommendation_evidence": opinion},
    )
    result = quality_summary("v", [], [], [mention])
    assert result["issues"] == [] and result["candidate_review_count"] == 1
    assert result["status"] == "UNKNOWN"  # no fabricated semantic PASS
    assert opinion["assessment_status"] == "NEEDS_REVIEW"  # POI/author gate is not altered
    mention.subject_role = "PRIMARY"
    assert quality_summary("v", [], [], [mention])["issue_count"] == 1
    mention.subject_role = "SECONDARY"
    opinion["reason_codes"] = ["WRONG_SUBJECT"]
    assert quality_summary("v", [], [], [mention])["issue_count"] == 1


def test_generation_mode_requires_an_exact_version_snapshot():
    from zhijian.services.note_quality import quality_summary

    snapshot = {"note_version_id": "v", "generation_mode": "HYBRID", "omitted_fact_count": 2}
    assert quality_summary("v", [], [], [], generation=snapshot)["generation_mode"] == "HYBRID"
    assert quality_summary("other", [], [], [], generation=snapshot)["generation_mode"] == "UNKNOWN"
    assert (
        quality_summary("v", [], [], [], generation={**snapshot, "generation_mode": "FAKE"})[
            "generation_mode"
        ]
        == "UNKNOWN"
    )


def test_review_claim_needs_both_exact_existing_statement_and_unique_named_source():
    from copy import deepcopy

    from zhijian.services.semantic_identity import resolve_review_claims_from_source

    segments = [
        SimpleNamespace(id="previous", text="海螺沟四号营地海拔3600米，可能高反。", corrected_text=""),
        SimpleNamespace(id="shared", text="除了高反人群，其他人都适合。第四个千山。", corrected_text=""),
    ]
    quote = "除了高反人群，其他人都适合"
    owner = {
        "entity_id": "sea",
        "raw_name": "海螺沟",
        "name": "海螺沟",
        "subject_role": "PRIMARY",
        "recommendation_evidence": {
            "statements": [
                {
                    "statement_id": "r",
                    "subject_entity_id": "sea",
                    "speaker": "AUTHOR",
                    "quote": quote,
                    "segment_ids": ["shared"],
                }
            ]
        },
    }
    unit = {
        "content_unit_id": "u",
        "unit_type": "PLACE_GUIDE",
        "anchor_entity_ids": ["sea"],
        "segment_ids": ["previous", "shared"],
    }
    claim = {
        "claim_id": "c",
        "text": quote,
        "supporting_quote": quote,
        "segment_ids": ["shared"],
        "subject_entity_ids": [],
        "attribution_status": "NEEDS_REVIEW",
    }
    fixed = deepcopy(claim)
    resolve_review_claims_from_source([owner], [unit], [fixed], segments)
    assert fixed["subject_entity_ids"] == ["sea"] and fixed["text"] == quote
    assert fixed["attribution_status"] == "RESOLVED_FROM_SOURCE"
    for entities, units in [
        ([{**owner, "recommendation_evidence": {"statements": []}}], [unit]),
        ([owner, {**owner, "entity_id": "other"}], [unit]),
        ([owner], [{**unit, "segment_ids": ["shared"]}]),
    ]:
        pending = deepcopy(claim)
        resolve_review_claims_from_source(entities, units, [pending], segments)
        assert pending == claim


def test_quarantined_fact_cannot_be_cited_under_a_place_to_clear_coverage():
    from zhijian.ai.note_evidence import validate_pack_coverage
    from zhijian.ai.reliability import AIProviderError

    fact = {
        "segment_ids": ["s"],
        "place_mention_ids": [],
        "attribution_status": "NEEDS_REVIEW",
        "supporting_quotes": ["除了高反人群，其他人都适合"],
    }
    section = {
        "segment_ids": ["s"],
        "place_mention_ids": ["wrong"],
        "supporting_quotes": fact["supporting_quotes"],
    }
    with pytest.raises(AIProviderError):
        validate_pack_coverage({"sections": [section]}, [fact])
    validate_pack_coverage({"sections": [{**section, "place_mention_ids": []}]}, [fact])


def test_citation_coverage_does_not_clear_an_unresolved_fact_owner():
    from zhijian.services.note_quality import quality_summary

    fact = {
        "segment_ids": ["s"],
        "place_mention_ids": [],
        "supporting_quotes": ["原句"],
        "attribution_status": "NEEDS_REVIEW",
    }
    section = {"id": "sec", "segment_ids": ["s"], "place_mention_ids": [], "evidence_quotes": ["原句"]}
    result = quality_summary("v", [section], [fact], [])
    assert result["evidence_represented_count"] == 1
    assert result["status"] == "NEEDS_REVIEW"
    assert result["issues"][0]["kind"] == "SOURCE_ATTRIBUTION_REVIEW"


def test_reduce_checks_literal_pack_sources_before_a_response_can_be_cached():
    from zhijian.ai.note_evidence import validate_pack_coverage
    from zhijian.ai.reliability import AIProviderError

    pack = [{"segment_ids": ["s"], "place_mention_ids": ["a"], "supporting_quotes": ["门票20元"]}]
    valid = {"segment_ids": ["s"], "place_mention_ids": ["a"], "supporting_quotes": ["门票20元"]}
    validate_pack_coverage({"sections": [valid]}, pack, source_texts={"s": "这里门票20元。"})
    for mutation in [
        {"supporting_quotes": ["门票20元，当前一直免费"]},
        {"place_mention_ids": ["other"]},
        {"segment_ids": ["foreign"]},
    ]:
        with pytest.raises(AIProviderError):
            validate_pack_coverage(
                {"sections": [{**valid, **mutation}]},
                pack,
                source_texts={"s": "这里门票20元。", "foreign": "门票20元"},
            )


def test_note_prompt_excludes_rejected_diagnostics_but_keeps_them_in_the_source():
    from copy import deepcopy

    from zhijian.ai.note_evidence import project_note_evidence

    index = [
        {
            "mention_id": "m",
            "name": "A",
            "theme_contexts": [],
            "recommendation_summary": {
                "status": "RECOMMENDED",
                "statements": [{"quote": "A值得去"}],
                "rejected_statements": [{"quote": "错误的推断"}],
                "rejected_context_annotations": [{"condition": "未经验证的条件"}],
                "future_diagnostic": "不应进入模型输入",
            },
        }
    ]
    original = deepcopy(index)
    projected = project_note_evidence(index)
    assert projected[0]["recommendation_summary"] == {
        "status": "RECOMMENDED",
        "statements": [{"quote": "A值得去"}],
    }
    assert index == original


def test_only_an_unanchored_list_before_all_place_guides_is_source_intro_context():
    from zhijian.services.note_structure import source_context_sections

    segments = [
        SimpleNamespace(id="intro", text="元旦跨年有哪些目的地", corrected_text=""),
        SimpleNamespace(id="place", text="第一个涠洲岛", corrected_text=""),
        SimpleNamespace(id="unknown", text="不明确的后续比较", corrected_text=""),
    ]
    units = [
        {"unit_type": "MULTI_PLACE_LIST", "segment_ids": ["intro"], "anchor_entity_ids": []},
        {"unit_type": "PLACE_GUIDE", "segment_ids": ["place"], "anchor_entity_ids": ["a"]},
        {"unit_type": "MULTI_PLACE_LIST", "segment_ids": ["unknown"], "anchor_entity_ids": []},
    ]
    result = source_context_sections([], units, segments)
    assert len(result) == 1 and result[0]["supporting_quotes"] == [segments[0].text]


def test_complete_raw_citations_do_not_hide_unfinished_model_synthesis():
    from zhijian.services.note_quality import quality_summary

    result = quality_summary(
        "v",
        [],
        [],
        [],
        generation={"note_version_id": "v", "generation_mode": "HYBRID", "omitted_fact_count": 15},
    )
    assert result["status"] == "NEEDS_REVIEW" and result["issue_count"] == 1
    assert result["issues"][0] == {"kind": "MODEL_FACTS_NOT_SUMMARIZED", "count": 15, "section_ids": []}


def test_note_pack_dedup_removes_only_proven_duplicate_citation_fields():
    from zhijian.ai.note_evidence import project_note_evidence

    index = [{"mention_id": "m", "theme_contexts": [], "quotes": ["完整原句"], "segment_ids": ["s"]}]
    pack = [{"supporting_quotes": ["完整原句"], "segment_ids": ["s"]}]
    projected = project_note_evidence(index, pack=pack)
    assert "quotes" not in projected[0] and "segment_ids" not in projected[0]
    assert index[0]["quotes"] == ["完整原句"]
    extra = [{**index[0], "quotes": ["另一条不能删除的原句"], "segment_ids": ["other"]}]
    assert project_note_evidence(extra, pack=pack) == extra
    assert project_note_evidence(index) == index  # legacy/global calls retain their full registry


def test_empty_and_duplicate_source_scaffolding_does_not_survive_quote_dedup():
    from zhijian.services.note_structure import _clean_source_subheadings

    body = (
        "### 海螺沟 · 来源描述\n来源描述（不作为独立推荐态度）：\n\n"
        "### 海螺沟 · 来源描述\n来源描述（不作为独立推荐态度）：\n> 完整原句\n\n"
        "### 海螺沟 · 来源描述\n> 另一原句\n\n### 保留的普通空标题\n"
    )
    clean = _clean_source_subheadings(body)
    assert clean.count("### 海螺沟 · 来源描述") == 1
    assert "> 完整原句" in clean and "> 另一原句" in clean
    assert "### 保留的普通空标题" in clean
