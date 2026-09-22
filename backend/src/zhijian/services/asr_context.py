from __future__ import annotations

import unicodedata
from hashlib import sha256

from zhijian.db.models import VideoAsset


def build_asr_context(asset: VideoAsset, *, max_terms: int = 40, max_chars: int = 800) -> dict:
    metadata = asset.metadata_json or {}
    candidates: list[tuple[str, str]] = [("TITLE", asset.title)]
    for value in metadata.get("tags", []) if isinstance(metadata.get("tags"), list) else []:
        candidates.append(("PLATFORM_TAG", str(value)))
    description_terms = metadata.get("asr_context_terms")
    if isinstance(description_terms, list):
        candidates.extend(("REVIEWED_DESCRIPTION_TERM", str(value)) for value in description_terms)
    terms: list[str] = []
    source_types: list[str] = []
    seen: set[str] = set()
    for source_type, raw in candidates:
        term = " ".join(unicodedata.normalize("NFKC", raw).split())[:80]
        key = term.casefold()
        if not term or key in seen:
            continue
        if len(" ".join([*terms, term])) > max_chars or len(terms) >= max_terms:
            break
        seen.add(key)
        terms.append(term)
        source_types.append(source_type)
    text = " ".join(terms)
    return {
        "text": text,
        "hash": sha256(text.encode()).hexdigest(),
        "source_types": list(dict.fromkeys(source_types)),
    }
