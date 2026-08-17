from __future__ import annotations

from urllib.parse import urlparse

from zhijian.domain.enums import JobType

RECRUITMENT_TERMS = ("招聘", "岗位", "事业单位", "公务员", "校招", "报名")
TRAVEL_TERMS = ("旅行", "旅游", "探店", "景区", "餐馆", "美食", "路线")


def classify_capture(locator: str, title: str = "", text: str = "") -> JobType:
    haystack = f"{locator} {title} {text[:4000]}".lower()
    if any(term.lower() in haystack for term in RECRUITMENT_TERMS):
        return JobType.RECRUITMENT
    if any(term.lower() in haystack for term in TRAVEL_TERMS):
        return JobType.TRAVEL

    host = urlparse(locator).netloc.lower() if "://" in locator else ""
    if host.endswith("bilibili.com"):
        return JobType.TRAVEL
    if host.endswith("mp.weixin.qq.com"):
        return JobType.UNKNOWN
    return JobType.UNKNOWN
