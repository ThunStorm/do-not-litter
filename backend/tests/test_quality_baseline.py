"""G0 gate self-tests, not synthetic human gold or model-quality measurements."""

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("quality_baseline", ROOT / "scripts/check_quality_baseline.py")
quality = importlib.util.module_from_spec(spec)
spec.loader.exec_module(quality)


def test_frozen_manifest_and_source_bindings():
    manifest = json.loads(quality.MANIFEST.read_text())
    rows, errors = quality.inspect_manifest(manifest)
    assert not errors
    assert all(r["judgment"] == "unjudged" for r in rows)
    december = ROOT / "backend/tests/fixtures/travel_pipeline/december_reverse_bv1hrxe6yebq"
    texts = {s["id"]: s["text"] for s in json.loads((december / "baseline.json").read_text())["segments"]}
    for r in rows:
        if r["id"].startswith("december:"):
            assert r["quote"] in "".join(texts[i] for i in r["segment_ids"])
    assert {c["id"] for c in manifest["categories"] if c["status"] == "BLOCKED_SOURCE"} == {
        "xiamen_food",
        "guizhou_full_video",
        "rapid_multiregion_holdout",
    }


@pytest.mark.parametrize(
    "mutation,code",
    [("negative", "MISSING_CRITICAL_QUALIFIER"), ("source", "CROSS_SOURCE"), ("poi", "WRONG_POI")],
)
def test_gate_rejects_missing_negation_cross_source_and_wrong_poi(mutation, code):
    manifest = json.loads(quality.MANIFEST.read_text())
    # Real source clause as structural test input. Copies exercise the detector only.
    expected = [
        r
        for c in manifest["categories"]
        for r in c["records"]
        if r["id"].startswith("december:") and "不" in r["quote"]
    ][:1]
    assert expected
    output = copy.deepcopy(expected)
    assert quality.contract_errors(expected, output) == []
    if mutation == "negative":
        output[0]["quote"] = output[0]["quote"].replace("不", "")
    elif mutation == "source":
        output[0]["identity"]["source_id"] = "another-source"
    else:
        output[0]["confirmed_poi"] = "wrong-poi"
    assert any(e.startswith(code) for e in quality.contract_errors(expected, output))


def test_one_to_one_metrics_and_unjudged_are_orthogonal_to_review():
    base = dict(dimension="fact", role="COMPARISON", judgment="judged", semantic_key="a")
    gold = [base, {**base, "semantic_key": "b"}]
    output = [
        {**base, "disposition": "NEEDS_REVIEW"},
        base,
        {**base, "semantic_key": "unknown", "judgment": "unjudged"},
    ]
    assert quality.score(gold, output, "fact", "COMPARISON") == dict(
        TP=1, FP=1, FN=1, precision=0.5, recall=0.5
    )
    assert quality.score([], [], "poi_identity", "RECOMMENDED")["precision"] is None
    assert quality.score(gold, output, "place", "COMPARISON")["TP"] is None
