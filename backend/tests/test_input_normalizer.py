from zhijian.services.input_normalizer import normalize_capture_input


def test_share_text_keeps_only_unique_url() -> None:
    value = "【国庆自驾】\nhttps://www.bilibili.com/video/BV1JH826zEKC，复制打开"
    normalized = normalize_capture_input(value)
    assert normalized.kind == "SHARE_TEXT_WITH_URL"
    assert normalized.selected_url == "https://www.bilibili.com/video/BV1JH826zEKC"
    assert normalized.discarded_text_length > 0


def test_multiple_distinct_urls_is_not_silently_selected() -> None:
    normalized = normalize_capture_input("https://b23.tv/a https://b23.tv/b")
    assert normalized.kind == "MULTIPLE_URLS"
    assert normalized.selected_url is None


def test_plain_url_and_text_are_distinct() -> None:
    assert normalize_capture_input("https://b23.tv/a").kind == "URL_ONLY"
    assert normalize_capture_input("这是一段普通正文").kind == "TEXT_ONLY"
