from zhijian.services.place_knowledge import normalize_insight


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
