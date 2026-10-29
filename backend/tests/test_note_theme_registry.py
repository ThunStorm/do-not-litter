import json
from copy import deepcopy
from types import SimpleNamespace

import pytest

from zhijian.ai.note_evidence import evidence_places, project_note_evidence
from zhijian.ai.request_compiler import compile_request


def sample():
    context = {
        "context_id": "tc1",
        "source_kind": "COVER_TEXT",
        "source_text": "8月目的地推荐",
        "segment_ids": [],
        "raw_time_text": "8月",
        "purpose": "VISIT",
        "activity": "GENERAL_VISIT",
        "scope": "VIDEO_THEME",
        "regions": [{"bbox": [0.1, 0.1, 0.8, 0.2]}],
        "cover_hash": "privatehash",
    }
    return [
        {
            "mention_id": f"p{i}",
            "segment_ids": ["seg"],
            "quotes": ["推荐甲地"],
            "theme_contexts": [
                {
                    "context": deepcopy(context),
                    "relation": "INCLUDED",
                    "segment_ids": ["seg"],
                    "supporting_quote": "推荐甲地",
                    "exclusions": [{"source_text": "8月中旬后不推荐"}],
                }
            ],
        }
        for i in range(2)
    ]


def test_shared_registry_keeps_sources_and_conditions_without_mutating_artifact():
    original = sample()
    before = deepcopy(original)
    result = project_note_evidence(original)
    assert original == before and len(result["contexts"]) == 1
    assert result["contexts"][0]["source_kind"] == "COVER_TEXT" and result["contexts"][0]["segment_ids"] == []
    assert "regions" not in result["contexts"][0] and "cover_hash" not in result["contexts"][0]
    assert result["places"][0]["theme_contexts"][0]["exclusions"][0]["source_text"] == "8月中旬后不推荐"
    assert "regions" in original[0]["theme_contexts"][0]["context"]


def test_undefined_and_conflicting_contexts_rejected():
    index = sample()
    index[1]["theme_contexts"][0]["context"]["source_text"] = "9月推荐"
    with pytest.raises(ValueError):
        project_note_evidence(index)
    value = project_note_evidence(sample())
    value["places"][0]["theme_contexts"][0]["context_id"] = "invented"
    with pytest.raises(ValueError):
        evidence_places(value)


def test_registry_short_ids_restore_and_legacy_index_stays_supported():
    segment = SimpleNamespace(id="seg", ordinal=0, snapshot_id="snap", text="推荐甲地", corrected_text="")
    for index in [sample(), project_note_evidence(sample())]:
        pack = [{"segment_ids": ["seg"], "supporting_quotes": ["推荐甲地"]}]
        body = (
            "Evidence Index："
            + json.dumps(index, ensure_ascii=False)
            + "\n仅据此生成全局笔记：\n"
            + json.dumps(pack, ensure_ascii=False)
        )
        request = compile_request("NOTE_REDUCE", [{"role": "user", "content": body}], [segment], "snap")
        assert "seg" not in request.messages[0]["content"].replace("segment_ids", "")
        restored = json.loads(
            request.decode(json.dumps({"sections": [{"segment_ids": [request.ids["seg"]]}]}))
        )
        assert restored["sections"][0]["segment_ids"] == ["seg"]


def test_cover_month_cannot_be_credited_to_platform_title():
    from zhijian.ai.note_evidence import validate_source_attribution
    from zhijian.ai.reliability import AIProviderError

    index = sample()
    with pytest.raises(AIProviderError):
        validate_source_attribution(
            {"sections": [{"summary": "来自视频标题：8月份推荐目的地"}]}, index, "暑假哪里适合去"
        )
    validate_source_attribution(
        {"sections": [{"summary": "来自封面文字：8月份推荐目的地"}]}, index, "暑假哪里适合去"
    )
    validate_source_attribution(
        {"sections": [{"summary": "来自视频标题：8月份推荐目的地"}]}, index, "8月份目的地推荐"
    )


def test_formal_title_and_cover_can_be_described_together():
    from zhijian.ai.note_evidence import validate_source_attribution

    validate_source_attribution(
        {"sections": [{"summary": "视频标题提暑假，封面8月推荐"}]}, sample(), "暑假哪里适合去"
    )


def test_separate_title_clause_does_not_capture_cover_month():
    from zhijian.ai.note_evidence import validate_source_attribution

    validate_source_attribution(
        {"sections": [{"summary": "视频标题提暑假，8月来自封面文字"}]}, sample(), "暑假哪里适合去"
    )
