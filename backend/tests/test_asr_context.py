from types import SimpleNamespace

from zhijian.services.asr_context import build_asr_context


def test_asr_context_uses_only_trusted_bounded_metadata() -> None:
    asset = SimpleNamespace(
        title="  大理古城  ",
        metadata_json={
            "tags": ["喜洲古镇", "大理古城", "喜洲古镇"],
            "asr_context_terms": ["人工核对店名"],
            "places": ["未确认 POI"],
            "note": "模型总结地点",
        },
    )

    context = build_asr_context(asset)

    assert context["text"] == "大理古城 喜洲古镇 人工核对店名"
    assert context["source_types"] == ["TITLE", "PLATFORM_TAG", "REVIEWED_DESCRIPTION_TERM"]
    assert "未确认" not in context["text"] and "模型总结" not in context["text"]
