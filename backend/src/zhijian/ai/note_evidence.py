"""Lossless semantic projection for note prompts; canonical artifacts retain full provenance."""

from copy import deepcopy

VERSION = "note-theme-registry-v1"
CONTEXT_FIELDS = {
    "context_id",
    "source_kind",
    "source_text",
    "segment_ids",
    "raw_time_text",
    "precision",
    "purpose",
    "activity",
    "scope",
    "scope_terms",
    "intent",
    "interpretation_status",
}
APPLICATION_FIELDS = {"context_id", "relation", "supporting_quote", "segment_ids", "exclusions"}


def project_note_evidence(index):
    if not any(row.get("theme_contexts") for row in index):
        return index
    contexts = {}
    places = []
    for row in index:
        place = deepcopy(row)
        apps = []
        for original in place.get("theme_contexts", []):
            context = original["context"]
            cid = context["context_id"]
            semantic = {k: v for k, v in context.items() if k in CONTEXT_FIELDS}
            semantic["source_label"] = (
                "封面原图文字（不是视频标题或字幕）"
                if context.get("source_kind") == "COVER_TEXT"
                else "正文转写原句"
            )
            if cid in contexts and contexts[cid] != semantic:
                raise ValueError("CONTEXT_ID_COLLISION")
            contexts[cid] = semantic
            app = {k: v for k, v in original.items() if k in APPLICATION_FIELDS}
            app["context_id"] = cid
            apps.append(app)
        place["theme_contexts"] = apps
        places.append(place)
    return {"version": VERSION, "contexts": list(contexts.values()), "places": places}


def evidence_places(value):
    if isinstance(value, list):
        return value
    if not isinstance(value, dict) or value.get("version") != VERSION:
        raise ValueError("INVALID_NOTE_EVIDENCE_REGISTRY")
    contexts = value.get("contexts")
    places = value.get("places")
    if not isinstance(contexts, list) or not isinstance(places, list):
        raise ValueError("INVALID_NOTE_EVIDENCE_REGISTRY")
    ids = [c["context_id"] for c in contexts]
    if len(ids) != len(set(ids)):
        raise ValueError("DUPLICATE_NOTE_CONTEXT_ID")
    if any(app.get("context_id") not in ids for p in places for app in p.get("theme_contexts", [])):
        raise ValueError("UNKNOWN_NOTE_CONTEXT_ID")
    return places


def validate_source_attribution(payload, index, official_title):
    """Reject a cover-only month falsely attributed to the formal platform title."""
    import re

    from zhijian.services.title_temporal import parse_title_temporal_context
    from zhijian.services.video_support import _months_in_text

    title_months = set(parse_title_temporal_context(official_title)["months"])
    cover_months = {
        m
        for row in index
        for app in row.get("theme_contexts", [])
        if app.get("context", {}).get("source_kind") == "COVER_TEXT"
        for m in _months_in_text(app["context"]["raw_time_text"])
    } - title_months
    texts = [str(payload.get("overview", ""))]
    for section in payload.get("sections", []):
        texts.extend(
            str(section.get(k, "")) for k in ["summary", "thesis", "heading", "body_markdown", "bullets"]
        )
    for month in cover_months:
        chinese = ("一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二")[month - 1]
        token = rf"(?:{month}|{chinese})月份?"
        if any(
            "封面" not in match.group(0)
            for text in texts
            for match in re.finditer(
                rf"(?:视频标题|来自标题|根据标题|依据标题)[^。！？\n；;，,]{{0,35}}{token}|{token}[^。！？\n；;，,]{{0,35}}(?:来自|依据|根据)(?:视频)?标题",
                text,
            )
        ):
            from zhijian.ai.reliability import AIProviderError

            raise AIProviderError(
                "AI_PROVIDER_SOURCE_ATTRIBUTION_INVALID", "封面月份被错误归因到正式标题", switch_model=False
            )
