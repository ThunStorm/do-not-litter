from zhijian.domain.enums import JobType
from zhijian.services.classifier import classify_capture


def test_bilibili_defaults_to_travel() -> None:
    assert classify_capture("https://www.bilibili.com/video/BV123") == JobType.TRAVEL


def test_recruitment_terms_take_priority() -> None:
    result = classify_capture("text://local", text="北京市事业单位公开招聘岗位表")
    assert result == JobType.RECRUITMENT
