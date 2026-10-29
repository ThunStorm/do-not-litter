"""Explicit real-model acceptance against an isolated SQLite backup, never production writes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.orm import Session
from zhijian.ai.job_config import SNAPSHOT_KEY, capture_ai_config
from zhijian.core.config import Settings
from zhijian.core.storage import require_idle
from zhijian.db.models import (
    AINote,
    AINoteVersion,
    ExternalCallAudit,
    Job,
    Segment,
    Setting,
    Transcript,
    VideoAsset,
)
from zhijian.db.session import build_engine
from zhijian.services.grounded_map import get_or_create_grounded_map
from zhijian.services.video_support import extract_place_mentions, generate_note


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--note-id", required=True)
    parser.add_argument("--phase", choices=["body", "ocr", "vision"], required=True)
    parser.add_argument(
        "--real",
        action="store_true",
        help="Explicit authorization to invoke configured models",
    )
    parser.add_argument("--render-note", action="store_true")
    parser.add_argument(
        "--replay-from",
        help="Explicit saved Map ID; deterministic replay, no extra Map call",
    )
    args = parser.parse_args()
    if not args.real:
        parser.error(
            "Real calls require --real; inspect the existing output files for read-only comparison"
        )
    prod = Settings()
    run = args.data_dir.resolve()
    if run == prod.data_dir.resolve() or not (run / "app.db").is_file():
        parser.error("An existing isolated backup is required")
    require_idle(prod.database_path)
    settings = Settings(
        _env_file=None,
        data_dir=run,
        secret_store="keychain",
        storage_config=run / "control/storage.json",
    )
    cover = (
        {"status": "DISABLED", "identity": "BENCHMARK_BODY_ONLY", "contexts": []}
        if args.phase == "body"
        else json.loads((run / f"{args.phase}-real.json").read_text())
    )
    if args.phase == "vision" and cover.get("method") != "VISION":
        parser.error(
            "Vision phase requires an actual successful image-model extraction; OCR fallback cannot substitute"
        )
    with Session(build_engine(settings), expire_on_commit=False) as db:
        note = db.get(AINote, args.note_id)
        if not note:
            parser.error("Unknown note in isolated backup")
        old = db.get(AINoteVersion, note.current_version_id)
        asset = db.get(VideoAsset, note.video_asset_id)
        transcript = db.scalar(
            select(Transcript).where(
                Transcript.video_asset_id == asset.id,
                Transcript.version == old.transcript_version,
            )
        )
        segments = list(
            db.scalars(
                select(Segment)
                .where(Segment.snapshot_id == transcript.metadata_json["snapshot_id"])
                .order_by(Segment.ordinal)
            )
        )
        routing = db.get(Setting, "model-routing").value_json
        profile = routing["primary_id"]
        for stage in ["GROUND_MAP", "NOTE_REDUCE", "GENERATE_AI_NOTE"]:
            db.merge(
                Setting(
                    key=f"ai-stage-policy:{stage}",
                    value_json={
                        "stage": stage,
                        "execution_mode": "REMOTE_ONLY",
                        "remote_profile_id": profile,
                        "max_attempts": 2,
                        "retry_count": 0,
                        "json_retry_count": 0,
                        "wall_time_seconds": 600,
                        "timeout_seconds": 300,
                        "max_output_tokens": 24000,
                        "chunk_size": 24000,
                        "allow_unverified_model": True,
                    },
                )
            )
        db.commit()
        # Resume a completed map without repeating paid calls. A new renderer remains explicit.
        state_path = run / f"{args.phase}-map.json"
        if state_path.exists():
            saved = json.loads(state_path.read_text())
            from zhijian.db.models import GroundedMapArtifact
            from zhijian.services.grounded_map import MAP_PROMPT_VERSION

            existing = db.get(GroundedMapArtifact, saved["artifact_id"])
            from zhijian.services.temporal_context import VERSION

            expected_cover = cover.get("semantic_identity", cover["identity"])
            if (
                not existing
                or existing.prompt_version != MAP_PROMPT_VERSION
                or existing.semantic_options_json.get("temporal_context_version") != VERSION
                or (args.replay_from and existing.semantic_options_json.get("temporal_replay", {}).get("source_artifact_id") != args.replay_from)
                or existing.semantic_options_json.get("cover_text_identity")
                != expected_cover
            ):
                state_path.rename(
                    state_path.with_name(
                        state_path.stem + "-" + saved["artifact_id"] + ".json"
                    )
                )
        if state_path.exists():
            saved = json.loads(state_path.read_text())
            from zhijian.db.models import GroundedMapArtifact, PlaceMention

            artifact = db.get(GroundedMapArtifact, saved["artifact_id"])
            job = db.get(Job, saved["job_id"])
            mentions = list(
                db.scalars(
                    select(PlaceMention).where(PlaceMention.submission_job_id == job.id)
                )
            )
        else:
            job = Job(
                job_type="TRAVEL",
                status="RUNNING",
                payload_json={
                    "note_id": note.id,
                    "acceptance_only": True,
                    SNAPSHOT_KEY: capture_ai_config(db, settings),
                },
            )
            db.add(job)
            db.commit()
            started = perf_counter()
            # Controlled input variants use real saved OCR/vision evidence. The model/Gateway is never mocked.
            if args.replay_from:
                from zhijian.db.models import GroundedMapArtifact
                from zhijian.services.temporal_replay import replay_temporal_map

                source = db.get(GroundedMapArtifact, args.replay_from)
                if not source:
                    parser.error("Unknown explicit source Map")
                artifact = replay_temporal_map(
                    db, source, asset, transcript, segments, cover
                )
            else:
                with patch(
                    "zhijian.services.cover_text.extract_cover_text", return_value=cover
                ):
                    artifact = get_or_create_grounded_map(
                        db, settings, asset, transcript, segments, job
                    )
            mentions = extract_place_mentions(
                db,
                settings,
                asset,
                None,
                segments,
                job,
                candidates=artifact.entities_json,
                claims=artifact.claims_json,
                content_units=artifact.content_units_json,
                cover_contexts=[
                    c
                    for c in artifact.semantic_options_json.get("temporal_contexts", [])
                    if c.get("source_kind") == "COVER_TEXT"
                ],
            )
            rows = []
            for m in mentions:
                rows.append(
                    {
                        "id": m.id,
                        "name": m.name,
                        "subject_role": m.subject_role,
                        "visit_intent": m.visit_intent,
                        "quote": m.quote,
                        "segment_ids": m.segment_ids_json,
                        "windows": m.metadata_json.get("visit_windows", []),
                        "applications": m.metadata_json.get(
                            "temporal_applications", []
                        ),
                        "analysis": m.metadata_json.get("temporal_analysis", {}),
                    }
                )
            audits = list(
                db.scalars(
                    select(ExternalCallAudit).where(ExternalCallAudit.job_id == job.id)
                )
            )
            result = {
                "phase": args.phase,
                "job_id": job.id,
                "artifact_id": artifact.id,
                "duration_seconds": perf_counter() - started,
                "entities": rows,
                "source_note_id": note.id,
                "old_version_id": old.id,
                "providers": [
                    {
                        "provider": a.provider,
                        "model": (a.request_meta_json or {}).get("model"),
                        "stage": (a.request_meta_json or {}).get("stage"),
                        "status": a.status,
                        "prompt_tokens": (a.response_meta_json or {}).get(
                            "prompt_tokens"
                        ),
                        "completion_tokens": (a.response_meta_json or {}).get(
                            "completion_tokens"
                        ),
                    }
                    for a in audits
                ],
                "cover_identity": cover.get("identity"),
                "production_modified": False,
                "poi_calls": 0,
            }
            state_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
            (run / f"{args.phase}-artifact.json").write_text(
                json.dumps(
                    {
                        "units": artifact.content_units_json,
                        "entities": artifact.entities_json,
                        "claims": artifact.claims_json,
                        "options": artifact.semantic_options_json,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        if args.render_note:
            job.status = "RUNNING"
            db.commit()
            version = generate_note(
                db, settings, asset, transcript, segments, job, mentions, artifact
            )
            (run / f"{args.phase}-note.md").write_text(version.markdown)
            (run / f"{args.phase}-new-version.json").write_text(
                json.dumps(
                    {
                        "new_version_id": version.id,
                        "old_version_id": old.id,
                        "artifact_id": artifact.id,
                        "rollback_current_version_id": old.id,
                        "database": str(run / "app.db"),
                        "production_modified": False,
                    },
                    indent=2,
                )
            )
        job.status = "COMPLETED"
        db.commit()
        print(
            json.dumps(
                {
                    "phase": args.phase,
                    "artifact_id": artifact.id,
                    "mentions": len(mentions),
                    "theme_members": sum(
                        bool(m.metadata_json.get("temporal_applications"))
                        for m in mentions
                    ),
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
