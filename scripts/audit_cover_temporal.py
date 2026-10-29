"""Read-only comparison of saved real-cover acceptance variants; never infer old Artifact bindings."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path

from zhijian.core.config import Settings
from zhijian.services.temporal_context import application_windows


def audit(run: Path):
    phases = {
        k: json.loads((run / f"{k}-map.json").read_text())
        for k in ["body", "ocr", "vision"]
    }

    def named(phase, needle):
        candidates = [e for e in phases[phase]["entities"] if needle in e["name"]]
        return candidates[0] if len(candidates) == 1 else None

    def times(phase, needle, kind):
        entity = named(phase, needle)
        return (
            [
                a["context"]["raw_time_text"]
                for a in entity["applications"]
                if a["context"]["source_kind"] == kind
            ]
            if entity
            else []
        )

    grass_body = times("body", "抓喜秀龙", "SOURCE_FACT")
    grass_ocr = times("ocr", "抓喜秀龙", "COVER_TEXT")
    grass_vision = times("vision", "抓喜秀龙", "COVER_TEXT")
    gulong = named("ocr", "古龙山")
    projection = json.loads((run / "projection-new-version.json").read_text())
    labels = json.loads((run / "case-gold.json").read_text())
    prod = Settings()
    with sqlite3.connect(prod.database_path.as_uri() + "?mode=ro", uri=True) as db:
        original = db.execute(
            "select grounded_map_artifact_id from ai_note_versions where id=?",
            (projection["original_version_id"],),
        ).fetchone()[0]
        baseline_file = run / "production-audit-baseline.json"
        if baseline_file.exists():
            latest_prod = json.loads(baseline_file.read_text())["max_created_at"]
        else:
            latest_prod = db.execute(
                "select max(created_at) from external_call_audits"
            ).fetchone()[0]
            baseline_file.write_text(
                json.dumps({"max_created_at": latest_prod}, indent=2)
            )
    with sqlite3.connect((run / "app.db").as_uri() + "?mode=ro", uri=True) as db:
        rows = db.execute(
            "select provider,operation,status,error_code,request_meta_json,response_meta_json from external_call_audits where created_at>? order by created_at",
            (latest_prod,),
        ).fetchall()
    counts = Counter()
    usage = Counter()
    attempts = []
    for provider, operation, status, code, request, response in rows:
        req, res = json.loads(request), json.loads(response)
        kind = "LOCAL" if provider == "ollama" else "REMOTE"
        reported = res.get("usage") or {}
        prompt = res.get("prompt_tokens")
        completion = res.get("completion_tokens")
        if prompt is None:
            prompt = reported.get("prompt_eval_count", reported.get("prompt_tokens"))
        if completion is None:
            completion = reported.get("eval_count", reported.get("completion_tokens"))
        counts[(provider, operation, status, code or "")] += 1
        if isinstance(prompt, int):
            usage[kind + "_prompt_tokens"] += prompt
        if isinstance(completion, int):
            usage[kind + "_completion_tokens"] += completion
        attempts.append(
            {
                "provider": provider,
                "model": req.get("model"),
                "stage": req.get("stage"),
                "status": status,
                "error_code": code,
                "prompt_tokens": prompt,
                "completion_tokens": completion,
            }
        )
    primary_ocr = json.loads((run / "ocr-real.json").read_text())
    primary_vision = json.loads(
        (run / "vision-effective-policy-primary.json").read_text()
    )
    challenge_ocr = json.loads((run / "ocr-challenge-results.json").read_text())
    challenge_vision = json.loads((run / "vision-challenge-results.json").read_text())
    for name in ["multiple", "blur"]:
        retry = json.loads((run / f"vision-{name}-retry.json").read_text())
        challenge_vision = [
            {**r, "retry": retry, "final_passed": retry["passed"]}
            if r["case"] == name
            else {**r, "final_passed": r.get("final_passed", r["passed"])}
            for r in challenge_vision
        ]
    gates = {
        "holiday_without_invented_month": bool(
            grass_body
            and all(
                not w["month"]
                for w in application_windows(named("body", "抓喜秀龙")["applications"])
            )
        ),
        "ocr_august_distinct_cover_source": any("8月" in t for t in grass_ocr),
        "vision_august_distinct_cover_source": any("8月" in t for t in grass_vision),
        "gulong_summer_rafting": bool(
            gulong
            and any(
                w.get("season") == "SUMMER"
                and w.get("semantics", {}).get("activity") == "RAFTING"
                for w in gulong["windows"]
            )
        ),
        "unassigned_grass_restriction_retained": any(
            "中旬" in r["source_text"] and "草原" in r["source_text"]
            for r in projection["unresolved_conditions"]
        ),
        "old_null_binding_preserved": original is None,
        "ocr_challenge_4_passed": all(r["passed"] for r in challenge_ocr),
        "vision_challenge_4_final_passed": all(
            r.get("final_passed", r["passed"]) for r in challenge_vision
        ),
    }
    result = {
        "scope": "One saved real video/cover plus four clearly synthetic cover-only challenge images; no ASR, video download, POI or production history update",
        "independent_labels": labels,
        "gates": gates,
        "all_target_gates_passed": all(gates.values()),
        "variants": {
            k: {
                "artifact_id": v["artifact_id"],
                "entities": len(v["entities"]),
                "theme_members": sum(bool(e["applications"]) for e in v["entities"]),
                "grass_time": times(k, "抓喜秀龙", "SOURCE_FACT")
                + times(k, "抓喜秀龙", "COVER_TEXT"),
            }
            for k, v in phases.items()
        },
        "recognition": {
            "ocr_primary_lines_preserved": all(
                x in "\n".join(r["text"] for r in primary_ocr["regions"])
                for x in labels["visible_primary"]
            ),
            "vision_primary_lines_preserved": all(
                x in "\n".join(r["text"] for r in primary_vision["regions"])
                for x in labels["visible_primary"]
            ),
            "ocr_ms": primary_ocr.get("duration_ms"),
            "vision_ms": primary_vision.get("duration_ms"),
        },
        "attempt_groups": [
            {
                "provider": k[0],
                "operation": k[1],
                "status": k[2],
                "error_code": k[3],
                "count": n,
            }
            for k, n in counts.items()
        ],
        "token_usage_measured": dict(usage),
        "cost": "UNKNOWN",
        "attempts": attempts,
        "ocr_challenges": challenge_ocr,
        "vision_challenges": challenge_vision,
        "new_version": projection,
        "production_original_artifact": original,
        "limits": [
            "User-reviewed broad semantic golden set is not completed.",
            "Model omissions and uncertain place names remain explicit review items.",
            "Final comparison uses the same actual saved Map facts with deterministic source replay, not three independently successful full-video model runs.",
        ],
    }
    (run / "acceptance-diff.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2)
    )
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-dir", type=Path, required=True)
    args = p.parse_args()
    result = audit(args.data_dir.resolve())
    print(
        json.dumps(
            {
                "gates": result["gates"],
                "token_usage": result["token_usage_measured"],
                "recognition": result["recognition"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
