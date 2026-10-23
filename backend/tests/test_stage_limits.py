from copy import deepcopy
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from zhijian.ai.job_config import EXECUTION_KEY, SNAPSHOT_KEY, capture_ai_config
from zhijian.ai.policies import resolve_stage_policy
from zhijian.ai.stage_limits import correction_batch_limits, limits_policy_version, request_timeout
from zhijian.core.config import Settings, get_settings
from zhijian.core.secret_store import build_secret_store
from zhijian.db.models import ExternalCallAudit, Setting
from zhijian.domain.schemas import TranscriptProcessingConfig
from zhijian.services.video_support import provider_for_role


@pytest.mark.parametrize(
    "stage,legacy,version,seconds,source",
    [
        (660, None, 2, 660, "STAGE_POLICY"),
        (660, 180, 2, 660, "STAGE_POLICY"),
        (None, None, 2, 300, "MODEL_PROFILE"),
        (None, 180, 2, 180, "LEGACY_TRANSCRIPT"),
        (660, None, 1, 300, "LEGACY_MINIMUM"),
        (660, 180, 1, 180, "LEGACY_MINIMUM"),
    ],
)
def test_timeout_precedence(stage, legacy, version, seconds, source):
    assert request_timeout(300, stage, legacy, version) == {"seconds": seconds, "source": source}


def test_old_jobs_stay_frozen_until_execution_config_is_replaced():
    job = SimpleNamespace(payload_json={SNAPSHOT_KEY: {"version": 1, "settings": {}}})
    original = deepcopy(job.payload_json)
    assert limits_policy_version(job) == 1
    assert job.payload_json == original
    job.payload_json[EXECUTION_KEY] = {"version": 1, "limits_policy_version": 2}
    assert limits_policy_version(job) == 2
    assert limits_policy_version(None) == 2


def test_correction_batch_limits_prefer_stage_and_keep_legacy_fallback():
    processing = TranscriptProcessingConfig(chunk_chars=5000, batch_size=24)
    old = resolve_stage_policy("TRANSCRIPT_CORRECTION")
    assert correction_batch_limits(old, processing) == (5000, 24)
    stage = resolve_stage_policy("TRANSCRIPT_CORRECTION", saved={"chunk_size": 3000, "batch_size": 16})
    assert correction_batch_limits(stage, processing) == (3000, 16)
    assert correction_batch_limits(stage, processing, 1) == (5000, 24)


def seed_model(db):
    db.add(
        Setting(
            key="model-profile:limits",
            value_json={
                "name": "Budget model",
                "provider": "DeepSeek",
                "model": "fixture",
                "base_url": "https://example.test/v1",
                "location": "REMOTE",
                "timeout_seconds": 300,
                "capabilities": ["STRUCTURED_EXTRACTION"],
            },
        )
    )
    db.add(Setting(key="model-routing", value_json={"primary_id": "limits"}))
    db.add(
        Setting(
            key="ai-stage-policy:GROUND_MAP",
            value_json={
                "execution_mode": "REMOTE_ONLY",
                "remote_profile_id": "limits",
                "timeout_seconds": 660,
            },
        )
    )
    db.commit()


def test_preview_uses_runtime_rules_and_does_not_write_or_invoke(client, app_and_session):
    app, factory = app_and_session
    settings = app.dependency_overrides[get_settings]()
    with factory() as db:
        seed_model(db)
        build_secret_store(settings.secret_store, settings.data_dir).set(
            "model-profile:limits:api-key", "test-key"
        )
        before_settings = [(x.key, deepcopy(x.value_json)) for x in db.scalars(select(Setting))]
        count = db.scalar(select(func.count()).select_from(ExternalCallAudit))
        provider, _, _ = provider_for_role(db, settings, "grounded_map")
        assert provider.primary.timeout == 660 and provider.primary.timeout_source == "STAGE_POLICY"
        assert capture_ai_config(db, settings)["limits_policy_version"] == 2
    response = client.post(
        "/api/ai/stage-policies/limits-preview",
        json={
            "stage": "GROUND_MAP",
            "capability": "STRUCTURED_EXTRACTION",
            "execution_mode": "REMOTE_ONLY",
            "timeout_seconds": 660,
            "wall_time_seconds": 500,
        },
    )
    assert response.status_code == 200, response.text
    preview = response.json()
    assert preview["request_timeouts"][0]["seconds"] == 660
    assert preview["request_timeouts"][0]["initial_ceiling_seconds"] == 500
    assert "test-key" not in response.text
    with factory() as db:
        assert [(x.key, x.value_json) for x in db.scalars(select(Setting))] == before_settings
        assert db.scalar(select(func.count()).select_from(ExternalCallAudit)) == count


def test_legacy_extraction_passes_stage_deadline(app_and_session, monkeypatch):
    from zhijian.db.models import Source, VideoAsset
    from zhijian.providers.llm import LLMResult
    from zhijian.services import video_support

    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/limits", title="fixture")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="fixture")
        db.add(asset)
        db.flush()
        _, segments = video_support.materialize_transcript(
            db,
            source,
            asset,
            [{"text": "去菜市场", "start_ms": 0, "end_ms": 1000}],
            source_kind="ASR",
        )
        db.add(Setting(key="ai-stage-policy:EXTRACT_TRAVEL_FACTS", value_json={"wall_time_seconds": 5}))
        db.flush()
        captured = []
        monkeypatch.setattr(
            video_support, "provider_for_role", lambda *args: (object(), "fixture", "fixture")
        )
        monkeypatch.setattr(video_support, "perf_counter", lambda: 100)

        def cached(*args, **kwargs):
            captured.append(kwargs["stage_deadline"])
            return LLMResult('{"places":[]}', "fixture", "fixture", {})

        monkeypatch.setattr(video_support, "_cached_stage_json", cached)
        video_support.extract_place_mentions(db, Settings(_env_file=None), asset, None, segments)
        assert captured == [105]


def test_legacy_note_passes_stage_deadline(app_and_session, monkeypatch):
    from zhijian.db.models import Source, VideoAsset
    from zhijian.providers.llm import LLMResult
    from zhijian.services import video_support

    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/note-limits", title="fixture")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator, title="fixture")
        db.add(asset)
        db.flush()
        transcript, segments = video_support.materialize_transcript(
            db,
            source,
            asset,
            [{"text": "去菜市场", "start_ms": 0, "end_ms": 1000}],
            source_kind="ASR",
        )
        db.add(Setting(key="ai-stage-policy:GENERATE_AI_NOTE", value_json={"wall_time_seconds": 5}))
        db.flush()
        captured = []
        monkeypatch.setattr(
            video_support, "provider_for_role", lambda *args: (object(), "fixture", "fixture")
        )
        monkeypatch.setattr(video_support, "perf_counter", lambda: 100)

        def cached(*args, **kwargs):
            captured.append((kwargs["stage"], kwargs["stage_deadline"]))
            return LLMResult(
                '{"overview":"fixture", "sections":[], "section_facts":[]}', "fixture", "fixture", {}
            )

        monkeypatch.setattr(video_support, "_cached_stage_json", cached)
        video_support.generate_note(db, Settings(_env_file=None), asset, transcript, segments)
        assert captured == [("GENERATE_AI_NOTE", 105)]
