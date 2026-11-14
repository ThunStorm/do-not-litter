from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from zhijian.services.place_knowledge import aggregate_place_knowledge, normalize_insight


def test_normalize_numeric_enum_and_time_insights() -> None:
    price_key, price = normalize_insight("PRICE", "人均八十")
    queue_key, queue = normalize_insight("QUEUE", "排队两小时")
    opinion_key, opinion = normalize_insight("AUTHOR_OPINION", "不推荐专程去")
    month_key, _ = normalize_insight("BEST_MONTH", "10月", "10")

    assert price_key == "PRICE:80-80CNY"
    assert price["normalized"] == {"min": 80, "max": 80, "unit": "CNY"}
    assert queue_key == "QUEUE:120-120MIN"
    assert queue["normalized"] == {"min": 120, "max": 120, "unit": "MIN"}
    assert opinion_key.startswith("OPINION:AVOID:")
    assert opinion["normalized"]["sentiment"] == "AVOID"
    assert month_key == "10"


def observation(source, text, context=None, observed=None, **kwargs):
    key, value = normalize_insight("PRICE", text)
    if context:
        value["comparison_context"] = context
    return SimpleNamespace(
        id=source + text,
        source_id=source,
        place_mention_id=None,
        status="ACTIVE",
        insight_type="PRICE",
        value_text=text,
        value_key=key,
        value_json=value,
        provenance="SOURCE_FACT",
        source_quote=text,
        segment_ids_json=["segment"],
        metadata_json={"observed_at": observed} if observed else {},
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        **kwargs,
    )


CONTEXT = dict(subject="成人门票", conditions="夏季平日", unit="元/人", period="2026-06")


@pytest.mark.parametrize(
    "field,value",
    [("subject", "儿童票"), ("conditions", "冬季周末"), ("unit", "元/车"), ("period", "2025-06")],
)
def test_different_conditions_are_not_conflicts(field, value):
    rows = [observation("a", "80元", CONTEXT), observation("b", "120元", {**CONTEXT, field: value})]
    prices = aggregate_place_knowledge(rows)["prices"]
    assert len(prices) == 2
    assert {p["state"] for p in prices} == {"UNDETERMINED"}
    assert sum(len(p["observations"]) for p in prices) == 2


def test_unknown_scope_never_becomes_conflict_or_current_fact():
    prices = aggregate_place_knowledge([observation("a", "80元"), observation("b", "120元")])["prices"]
    assert {p["state"] for p in prices} == {"UNDETERMINED"}
    assert not any(p["current"] for p in prices)
    assert all(p["observations"][0]["observed_at"] is None for p in prices)
    assert all(p["observations"][0]["time_basis"] == "RECORDED" for p in prices)


def test_comparable_contradiction_and_repeat_source_count():
    rows = [
        observation("a", "80元", CONTEXT),
        observation("a", "80元", CONTEXT),
        observation("b", "80元", CONTEXT),
        observation("c", "120元", CONTEXT),
    ]
    prices = aggregate_place_knowledge(rows)["prices"]
    assert {p["state"] for p in prices} == {"CONFLICT"}
    assert prices[0]["source_count"] == 2
    assert len(prices[0]["observations"]) == 3
    assert prices[0]["independent_verification"] == "UNKNOWN"


def test_observation_time_is_separate_from_collection_and_accepts_naive_and_z():
    rows = [
        observation("a", "80元", CONTEXT, "2025-01-01T00:00:00"),
        observation("b", "80元", CONTEXT, "2025-02-01T00:00:00Z"),
    ]
    price = aggregate_place_knowledge(rows)["prices"][0]
    assert price["observations"][0]["observed_at"].startswith("2025-02")
    assert price["observations"][0]["recorded_at"].startswith("2026-01")
    assert price["state"] == "CONSENSUS"


def test_decimal_price_is_not_truncated_or_rejected():
    key, value = normalize_insight("PRICE", "8.5元")
    assert value["normalized"]["min"] == 8.5
    assert "8.5" in key


@pytest.mark.parametrize(
    "invalid", [None, {}, {"min": "invalid", "max": 5, "unit": "CNY"}, {"min": 8, "max": 5, "unit": "CNY"}]
)
def test_malformed_legacy_bounds_are_not_treated_as_conflict(invalid):
    first, second = observation("a", "80元", CONTEXT), observation("b", "120元", CONTEXT)
    first.value_json["normalized"] = invalid
    assert {p["state"] for p in aggregate_place_knowledge([first, second])["prices"]} == {"UNDETERMINED"}


def test_broad_numeric_range_cannot_bridge_two_contradictory_records():
    rows = [
        observation("a", "70-100元", CONTEXT),
        observation("b", "70-80元", CONTEXT),
        observation("c", "90-100元", CONTEXT),
    ]
    prices = aggregate_place_knowledge(rows)["prices"]
    assert len(prices) == 2
    assert {p["state"] for p in prices} == {"CONFLICT"}
    assert sum(len(p["observations"]) for p in prices) == 3
