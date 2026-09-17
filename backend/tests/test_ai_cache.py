import pytest

from zhijian.ai.budget import AIBudgetExceeded, ensure_ai_budget
from zhijian.ai.cache import cached_json_result, legacy_cache_key
from zhijian.ai.structured_output import validate_structured_output
from zhijian.db.models import AICacheEntry, ExternalCallAudit, Job, Setting
from zhijian.providers.llm import LLMResult


def test_exact_ai_cache_reuses_result_and_force_refresh_keeps_previous(app_and_session) -> None:
    _, factory = app_and_session
    calls = 0
    with factory() as db:
        job = Job(job_type="TRAVEL", status="RUNNING", payload_json={})
        db.add(job)
        db.commit()

        def call() -> LLMResult:
            nonlocal calls
            calls += 1
            return LLMResult('{"ok":true}', "ollama", "qwen", {"prompt_eval_count": 3, "eval_count": 1})

        arguments = {
            "job": job,
            "stage": "TRANSCRIPT_CORRECTION",
            "capability": "TRANSCRIPT_CORRECTION",
            "provider": "ollama",
            "model": "qwen",
            "messages": [{"role": "user", "content": "same evidence"}],
            "semantic_options": {"temperature": 0.1},
            "cache_enabled": True,
            "call": call,
        }
        first = cached_json_result(db, force_regenerate=False, **arguments)
        second = cached_json_result(db, force_regenerate=False, **arguments)
        refreshed = cached_json_result(db, force_regenerate=True, **arguments)
        assert first.content == second.content == refreshed.content
        assert calls == 2
        entries = db.query(AICacheEntry).order_by(AICacheEntry.created_at).all()
        assert len(entries) == 2 and entries[-1].previous_entry_id == entries[0].id
        cache_audits = [
            row for row in db.query(ExternalCallAudit).all() if row.request_meta_json.get("cache_hit")
        ]
        assert len(cache_audits) == 1


def test_invalid_cache_hit_is_audited_and_replaced(app_and_session) -> None:
    _, factory = app_and_session
    calls = 0
    messages = [{"role": "user", "content": "same grounded evidence"}]
    semantic_options = {"temperature": 0.1}
    with factory() as db:
        job = Job(job_type="TRAVEL", status="RUNNING", payload_json={})
        db.add(job)
        db.flush()
        stale = AICacheEntry(
            cache_key=legacy_cache_key(
                stage="GROUND_MAP",
                capability="STRUCTURED_EXTRACTION",
                provider="ollama",
                model="qwen",
                messages=messages,
                semantic_options=semantic_options,
            ),
            stage="GROUND_MAP",
            capability="STRUCTURED_EXTRACTION",
            provider="ollama",
            model="qwen",
            result_json={
                "content": '{"section_facts":[',
                "provider": "ollama",
                "model": "qwen",
                "usage": {"prompt_eval_count": 99},
            },
        )
        db.add(stale)
        db.commit()

        def call() -> LLMResult:
            nonlocal calls
            calls += 1
            return LLMResult(
                '{"section_facts":[],"places":[],"warnings":[]}',
                "ollama",
                "qwen",
                {"prompt_eval_count": 4},
            )

        arguments = {
            "job": job,
            "stage": "GROUND_MAP",
            "capability": "STRUCTURED_EXTRACTION",
            "provider": "ollama",
            "model": "qwen",
            "messages": messages,
            "semantic_options": semantic_options,
            "location": "LOCAL",
            "cache_enabled": True,
            "call": call,
            "validate": lambda result: validate_structured_output(
                result.content, "GROUND_MAP", result.metadata
            ),
        }
        first = cached_json_result(db, force_regenerate=False, **arguments)
        second = cached_json_result(db, force_regenerate=False, **arguments)

        assert first.content == second.content
        assert calls == 1
        entries = db.query(AICacheEntry).order_by(AICacheEntry.created_at).all()
        assert len(entries) == 2 and entries[-1].previous_entry_id == stale.id
        audits = db.query(ExternalCallAudit).order_by(ExternalCallAudit.created_at).all()
        assert [row.status for row in audits] == ["SKIPPED", "COMPLETED"]
        assert [row.error_code for row in audits] == ["AI_CACHE_INVALID", None]
        assert audits[0].request_meta_json == {
            "stage": "GROUND_MAP",
            "model": "qwen",
            "location": "LOCAL",
            "cache_hit": True,
            "cache_invalid": True,
            "cache_entry_id": stale.id,
        }
        assert audits[1].request_meta_json["cache_entry_id"] == entries[-1].id
        ensure_ai_budget(db, job, location="LOCAL", input_chars=4)


def test_valid_legacy_cache_is_reused_without_provider_call(app_and_session) -> None:
    _, factory = app_and_session
    messages = [{"role": "user", "content": "legacy evidence"}]
    semantic_options: dict = {}
    with factory() as db:
        legacy = AICacheEntry(
            cache_key=legacy_cache_key(
                stage="GROUND_MAP",
                capability="STRUCTURED_EXTRACTION",
                provider="ollama",
                model="qwen",
                messages=messages,
                semantic_options=semantic_options,
            ),
            stage="GROUND_MAP",
            capability="STRUCTURED_EXTRACTION",
            provider="ollama",
            model="qwen",
            result_json={
                "content": '{"section_facts":[],"places":[],"warnings":[]}',
                "provider": "ollama",
                "model": "qwen",
                "usage": {},
            },
        )
        db.add(legacy)
        db.commit()

        result = cached_json_result(
            db,
            job=None,
            stage="GROUND_MAP",
            capability="STRUCTURED_EXTRACTION",
            provider="ollama",
            model="qwen",
            messages=messages,
            semantic_options=semantic_options,
            cache_enabled=True,
            force_regenerate=False,
            call=lambda: pytest.fail("合法旧缓存不应调用 Provider"),
            validate=lambda item: validate_structured_output(item.content, "GROUND_MAP", item.metadata),
        )

        assert result.content == legacy.result_json["content"]
        assert db.query(AICacheEntry).count() == 1


def test_local_and_non_llm_calls_do_not_consume_remote_attempt_limit(app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        job = Job(job_type="TRAVEL", status="RUNNING", payload_json={})
        db.add(job)
        db.flush()
        db.add(Setting(key="app:general", value_json={"ai_max_model_attempts_per_job": 1}))
        db.add_all(
            [
            ExternalCallAudit(
                job_id=job.id,
                capability="LLM",
                provider="ollama",
                operation="TRANSCRIPT_CORRECTION",
                status="COMPLETED",
                request_meta_json={"location": "LOCAL", "model": "qwen"},
                response_meta_json={},
            ),
            ExternalCallAudit(
                job_id=job.id,
                capability="VIDEO_MEDIA",
                provider="yt-dlp",
                operation="audio-only",
                status="COMPLETED",
                request_meta_json={},
                response_meta_json={},
            ),
            ]
        )
        db.commit()
        ensure_ai_budget(db, job, location="LOCAL", input_chars=40)
        ensure_ai_budget(
            db,
            job,
            location="REMOTE",
            input_chars=40,
            provider="remote",
            model="model-a",
            profile_id="profile-a",
        )


def test_remote_attempt_limit_is_per_profile_and_excludes_cache_hits(app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        job = Job(job_type="TRAVEL", status="RUNNING", payload_json={})
        db.add_all(
            [job, Setting(key="app:general", value_json={"ai_max_model_attempts_per_job": 1})]
        )
        db.flush()
        db.add_all(
            [
                ExternalCallAudit(
                    job_id=job.id,
                    capability="LLM",
                    provider="remote",
                    operation="fixture",
                    status="COMPLETED",
                    request_meta_json={
                        "location": "REMOTE",
                        "model": "model-a",
                        "profile_id": "profile-a",
                    },
                    response_meta_json={},
                ),
                ExternalCallAudit(
                    job_id=job.id,
                    capability="LLM",
                    provider="remote",
                    operation="fixture",
                    status="COMPLETED",
                    request_meta_json={
                        "location": "REMOTE",
                        "model": "model-b",
                        "profile_id": "profile-b",
                        "cache_hit": True,
                    },
                    response_meta_json={},
                ),
            ]
        )
        db.commit()
        with pytest.raises(AIBudgetExceeded):
            ensure_ai_budget(
                db,
                job,
                location="REMOTE",
                input_chars=40,
                provider="remote",
                model="model-a",
                profile_id="profile-a",
            )
        ensure_ai_budget(
            db,
            job,
            location="REMOTE",
            input_chars=40,
            provider="remote",
            model="model-b",
            profile_id="profile-b",
        )


def test_local_usage_does_not_consume_remote_budget(app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        job = Job(job_type="TRAVEL", status="RUNNING", payload_json={})
        db.add_all(
            [
                job,
                Setting(key="app:general", value_json={"ai_max_remote_prompt_tokens_per_job": 1000}),
            ]
        )
        db.flush()
        db.add(
            ExternalCallAudit(
                job_id=job.id,
                capability="LLM",
                provider="ollama",
                operation="GENERATE_AI_NOTE",
                status="COMPLETED",
                request_meta_json={"location": "LOCAL"},
                response_meta_json={"prompt_tokens": 999},
            )
        )
        db.commit()
        ensure_ai_budget(db, job, location="REMOTE", input_chars=4)


def test_remote_usage_does_not_consume_local_budget(app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        job = Job(job_type="TRAVEL", status="RUNNING", payload_json={})
        db.add_all(
            [
                job,
                Setting(key="app:general", value_json={"ai_max_local_prompt_tokens_per_job": 1000}),
            ]
        )
        db.flush()
        db.add(
            ExternalCallAudit(
                job_id=job.id,
                capability="LLM",
                provider="remote",
                operation="GENERATE_AI_NOTE",
                status="COMPLETED",
                request_meta_json={"location": "REMOTE"},
                response_meta_json={"prompt_tokens": 999},
            )
        )
        db.commit()
        ensure_ai_budget(db, job, location="LOCAL", input_chars=4)


def test_cache_hit_does_not_consume_budget_and_records_location(app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        job = Job(job_type="TRAVEL", status="RUNNING", payload_json={})
        db.add(job)
        db.commit()
        arguments = {
            "job": job,
            "stage": "GENERATE_AI_NOTE",
            "capability": "LLM",
            "provider": "remote",
            "model": "strong",
            "messages": [{"role": "user", "content": "same"}],
            "semantic_options": {},
            "location": "REMOTE",
            "cache_enabled": True,
            "call": lambda: LLMResult("{}", "remote", "strong", {"prompt_tokens": 99}),
        }
        cached_json_result(db, force_regenerate=False, **arguments)
        cached_json_result(db, force_regenerate=False, **arguments)
        audit = db.query(ExternalCallAudit).one()
        assert audit.request_meta_json["location"] == "REMOTE"
        db.add(Setting(key="app:general", value_json={"ai_max_remote_prompt_tokens_per_job": 1000}))
        db.commit()
        ensure_ai_budget(db, job, location="REMOTE", input_chars=4)
