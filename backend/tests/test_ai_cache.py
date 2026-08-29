import pytest

from zhijian.ai.budget import AIBudgetExceeded, ensure_ai_budget
from zhijian.ai.cache import cached_json_result
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


def test_budget_excludes_cache_hits_and_blocks_next_model_attempt(app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        job = Job(job_type="TRAVEL", status="RUNNING", payload_json={})
        db.add(job)
        db.flush()
        db.add(Setting(key="app:general", value_json={"ai_max_model_attempts_per_job": 1}))
        db.add(
            ExternalCallAudit(
                job_id=job.id,
                capability="TRANSCRIPT_CORRECTION",
                provider="ollama",
                operation="TRANSCRIPT_CORRECTION",
                status="COMPLETED",
                request_meta_json={"cache_hit": False},
                response_meta_json={},
            )
        )
        db.commit()
        with pytest.raises(AIBudgetExceeded):
            ensure_ai_budget(db, job, location="LOCAL", input_chars=40)
        db.query(ExternalCallAudit).update({"request_meta_json": {"cache_hit": True}})
        db.commit()
        ensure_ai_budget(db, job, location="LOCAL", input_chars=40)
