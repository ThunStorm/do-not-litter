"""Offline temporal counterexamples; no provider calls or production writes."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from zhijian.core.config import Settings
from zhijian.db.models import Source, VideoAsset
from zhijian.services.title_temporal import parse_title_temporal_context, title_projection
from zhijian.services.travel_timing import has_temporal_scope, matches_window, window_label
from zhijian.services.video_support import (
    TEMPORAL_CUE,
    _visit_windows_from_candidate,
    extract_place_mentions,
    materialize_transcript,
)


@pytest.mark.parametrize("word", ["春天", "夏天", "秋天", "冬天", "暑假", "寒假", "盛夏"])
def test_temporal_vocabulary_and_holiday_precision(word):
    quote = f"{word}推荐前往"
    assert TEMPORAL_CUE.search(quote) and has_temporal_scope(quote)
    windows = _visit_windows_from_candidate({}, ["s"], {"s": quote})
    assert len(windows) == 1
    if word in {"暑假", "寒假"}:
        w = SimpleNamespace(**windows[0], provenance="SOURCE_FACT")
        assert w.month is None and w.season is None
        assert w.semantics["precision"] == "HOLIDAY"
        assert window_label(w) == word
        assert not matches_window(w, month=8)


def test_title_modifiers_do_not_erase_geographic_scope():
    m = SimpleNamespace(
        name="甲地",
        raw_name="甲地",
        subject_role="PRIMARY",
        visit_intent="RECOMMENDED",
        poi_policy="RESOLVE",
        extraction_status="EXTRACTED",
        content_unit_id="u",
    )
    for title in ["8月份宝藏目的地推荐！", "暑假到底哪里人少景美又避暑圣地？"]:
        ctx = parse_title_temporal_context(title)
        assert title_projection(ctx, m, "推荐甲地", [])["status"] == "INHERITED"
    ctx = parse_title_temporal_context("8月份川西赏花目的地推荐")
    assert title_projection(ctx, m, "推荐甲地", [])["status"] == "OUT_OF_SCOPE"


@pytest.mark.parametrize("quote", ["去年8月客流最多", "每年7月15日到8月15日游客最多"])
def test_background_cannot_be_promoted_by_model_window(quote):
    windows = _visit_windows_from_candidate(
        {
            "visit_windows": [
                {"suitability": "RECOMMENDED", "month": 8, "segment_ids": ["s"], "source_text": quote}
            ]
        },
        ["s"],
        {"s": quote},
    )
    assert windows and all(w["suitability"] == "INFORMATIONAL" for w in windows)


def test_history_modifier_split_before_month_is_not_lost():
    windows = _visit_windows_from_candidate({}, ["a", "b"], {"a": "去年", "b": "8月推荐前往。"})
    assert len(windows) == 1
    assert windows[0]["suitability"] == "INFORMATIONAL"
    assert windows[0]["source_text"] == "去年8月推荐前往"
    assert windows[0]["segment_ids"] == ["a", "b"]


def test_saved_gulongshan_transcript_evidence_is_reproducible():
    fixture = json.loads((Path(__file__).parent / "fixtures/video_temporal_context.json").read_text())
    assert fixture["grounded_map_artifact_id"] is None
    rows = fixture["segments"]
    assert len({s["snapshot_id"] for s in rows}) == 1
    assert rows[1]["ordinal"] == rows[0]["ordinal"] + 1
    texts = {s["id"]: s["corrected_text"] or s["text"] for s in rows}
    windows = _visit_windows_from_candidate({}, list(texts), texts)
    summer = [w for w in windows if w["season"] == "SUMMER"]
    assert summer and summer[0]["semantics"]["activity"] == "RAFTING"
    assert summer[0]["segment_ids"] == list(texts)
    assert summer[0]["month"] is None


@pytest.mark.parametrize("mode", ["valid", "other_subject", "reversed", "skipped", "tampered"])
def test_claim_owns_full_contiguous_evidence_independently_of_mention(app_and_session, mode):
    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="fixture://temporal-claim")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="旅行")
        db.add(asset)
        db.flush()
        _, segments = materialize_transcript(
            db,
            source,
            asset,
            [
                {"text": text, "start_ms": i * 1000, "end_ms": (i + 1) * 1000}
                for i, text in enumerate(
                    ["古龙山可以漂流，", "夏天去肯定是一个比较好的体验了。", "别处的背景。"]
                )
            ],
            source_kind="ASR",
        )
        ids = [s.id for s in segments[:2]]
        quote = "".join(s.text for s in segments[:2])
        if mode == "reversed":
            ids.reverse()
        if mode == "skipped":
            ids = [segments[0].id, segments[2].id]
        if mode == "tampered":
            quote = "古龙山夏天最佳"
        result = extract_place_mentions(
            db,
            Settings(_env_file=None),
            asset,
            None,
            segments,
            candidates=[
                {
                    "name": "古龙山",
                    "entity_id": "a",
                    "segment_ids": [segments[0].id],
                    "quote": "古龙山",
                    "subject_role": "PRIMARY",
                    "visit_intent": "RECOMMENDED",
                    "poi_policy": "RESOLVE",
                }
            ],
            claims=[
                {
                    "subject_entity_ids": ["b" if mode == "other_subject" else "a"],
                    "segment_ids": ids,
                    "supporting_quote": quote,
                }
            ],
        )
        windows = result[0].metadata_json["visit_windows"]
        if mode == "valid":
            assert len(windows) == 1
            assert windows[0]["segment_ids"] == ids
            assert windows[0]["source_text"] == quote.rstrip("。")
            assert windows[0]["season"] == "SUMMER"
            assert windows[0]["semantics"]["activity"] == "RAFTING"
        else:
            assert not windows
