import json
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import select

from zhijian.ai.cache import cache_key
from zhijian.ai.gateway import AIWorkloadGateway
from zhijian.ai.model_registry import business_assessments, business_probe_status
from zhijian.ai.reliability import AIProviderError, ModelReliabilityPolicy
from zhijian.ai.request_compiler import compact, compile_request
from zhijian.ai.request_metrics import request_metrics
from zhijian.ai.structured_output import parse_json_with_quality
from zhijian.core.time import utc_now
from zhijian.db.models import AICacheEntry, Segment
from zhijian.providers.llm import FallbackLLMProvider, LLMResult, OllamaProvider, safe_runtime_metadata
from zhijian.services.evidence_trace import evidence_trace
from zhijian.services.jobs import JobCancelled


@pytest.mark.parametrize(
    "base,model,expected",
    [
        ("https://token.sensenova.cn/v1", "deepseek-v4-flash", {"reasoning_effort": "none"}),
        ("https://token.sensenova.cn/v1", "glm-5.2", {"reasoning_effort": "none"}),
        ("https://openrouter.ai/api/v1", "openrouter/free", {"reasoning": {"enabled": False}}),
        ("https://token.sensenova.cn/v1", "sensenova-6.8-flash-lite", {"reasoning_effort": "none"}),
        ("https://api.deepseek.com/v1", "deepseek-v4-flash", {"thinking": {"type": "disabled"}}),
        ("https://other.fixture/v1", "deepseek-v4-flash", {}),
    ],
)
def test_thinking_control_is_specific_to_actual_entry(monkeypatch, base, model, expected):
    from zhijian.providers.llm import OpenAICompatibleProvider, ProviderRequestOptions

    sent = []

    def post(url, **kwargs):
        sent.append(kwargs["json"])
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "choices": [{"message": {"content": '{"changes":[]}'}, "finish_reason": "stop"}],
            },
        )

    monkeypatch.setattr(httpx, "post", post)
    provider = OpenAICompatibleProvider("openai-compatible", base, "fixture-account")
    result = provider.generate_json([], model=model, options=ProviderRequestOptions(thinking=False))
    assert result.metadata["request_metrics"]["raw_request_bytes"] == len(
        httpx.Request("POST", base, json=sent[0]).content
    )
    assert {k: sent[0][k] for k in ("thinking", "reasoning_effort", "reasoning") if k in sent[0]} == expected


def segments(snapshot="snapshot-a"):
    return [
        Segment(
            id="seg_" + str(index) * 32,
            snapshot_id=snapshot,
            ordinal=index,
            text=text,
            raw_text=text,
            corrected_text="",
            locator_json={"start_ms": index, "end_ms": index + 1},
        )
        for index, text in enumerate(["西安和洛阳10月门票20元，不推荐周末。", "最后一段推荐水陆庵。"], 1)
    ]


def request(values):
    return [
        {"role": "system", "content": "按逐字 Evidence 返回 JSON，不新增事实。"},
        {
            "role": "user",
            "content": "\n".join(
                f"[segment:{item.id} {item.ordinal}-{item.ordinal + 1}ms] {item.text}" for item in values
            ),
        },
    ]


def test_codec_preserves_text_quotes_and_stable_split_identity():
    values = segments()
    values[0].text += "\n[segment:" + values[1].id + " 2-3ms] 这是原文中的标签，不能修改。"
    compiled = compile_request("GROUND_MAP", request(values), values, "snapshot-a")
    assert values[0].text in compiled.messages[-1]["content"]
    split = compile_request("GROUND_MAP", request(values[1:]), values, "snapshot-a")
    assert "[segment:s2 " in split.messages[-1]["content"]
    output = {
        "section_facts": [],
        "places": [{"segment_ids": ["s2"], "quote": values[1].text}],
        "warnings": [],
    }
    decoded = json.loads(split.decode(compact(output)))
    assert decoded["places"][0] == {"segment_ids": [values[1].id], "quote": values[1].text}
    assert compiled.identity == compile_request("GROUND_MAP", request(values), values, "snapshot-a").identity
    with pytest.raises(AIProviderError):
        split.decode('{"places":[{"segment_ids":["s1"]}]}')
    with pytest.raises(AIProviderError):
        split.decode('{"places":[{"segment_ids":["s99"]}]}')
    with pytest.raises(ValueError):
        compile_request("GROUND_MAP", request(values), values, "wrong-snapshot")


def test_correction_deduplicates_context_but_restricts_targets():
    values = segments()

    def entry(item):
        return {"id": item.id, "text": item.text}

    body = {
        "video_title": "旅行",
        "items": [{"target": entry(values[1]), "context_before": [entry(values[0])], "context_after": []}]
        * 2,
    }
    messages = [{"role": "system", "content": "校对"}, {"role": "user", "content": compact(body)}]
    compiled = compile_request("TRANSCRIPT_CORRECTION", messages, values, "snapshot-a")
    data = json.loads(compiled.messages[-1]["content"])
    assert len(data["segments"]) == 2
    assert data["segments"][0]["text"] == values[0].text
    assert request_metrics(messages)["duplicate_context_chars"] > 0
    assert request_metrics(compiled.messages)["duplicate_context_chars"] == 0
    assert data["target_ids"] == ["s2"]
    with pytest.raises(AIProviderError):
        compiled.decode('{"changes":[{"segment_id":"s1","corrected_text":"无权修改"}]}')


def test_local_ids_are_namespaced_by_source_interval_and_references_are_checked():
    values = segments()
    payload = {
        "content_units": [{"content_unit_id": "u1", "segment_ids": ["s1"]}],
        "entities": [{"entity_id": "e1", "content_unit_id": "u1", "segment_ids": ["s1"]}],
        "claims": [
            {"claim_id": "c1", "content_unit_id": "u1", "subject_entity_ids": ["e1"], "segment_ids": ["s1"]}
        ],
        "relations": [{"source_entity_id": "e1", "target_entity_id": "e1"}],
        "warnings": [],
    }
    compiler = compile_request("GROUND_MAP", request(values[:1]), values, "snapshot-a")
    decoded = json.loads(compiler.decode(compact(payload)))
    assert decoded["claims"][0]["subject_entity_ids"] == [decoded["entities"][0]["entity_id"]]
    payload["relations"][0]["target_entity_id"] = "unknown"
    with pytest.raises(AIProviderError):
        compiler.decode(compact(payload))
    payload["relations"] = []
    payload["entities"].append(dict(payload["entities"][0]))
    with pytest.raises(AIProviderError):
        compiler.decode(compact(payload))


@pytest.mark.parametrize(
    "text,quality",
    [
        ('{"ok":true}', "DIRECT_VALID"),
        ('```json\n{"ok":true}\n```', "NORMALIZED_VALID"),
        ('\ufeff{"ok":true}', "NORMALIZED_VALID"),
        ('{"ok":true,}', "DETERMINISTIC_REPAIRED"),
    ],
)
def test_parse_quality(text, quality):
    assert parse_json_with_quality(text)[1] == quality


@pytest.mark.parametrize("text", ['{"ok":true', '{"ok":true}另一个{}', "[1,2]", ""])
def test_invalid_or_incomplete_json_is_rejected(text):
    with pytest.raises(AIProviderError):
        parse_json_with_quality(text)


def test_repair_does_not_change_literal_quote():
    assert parse_json_with_quality('{"quote":"原文,}不能改",}')[0]["quote"] == "原文,}不能改"
    assert parse_json_with_quality('说明：{"ok":true}')[1:] == (
        "DETERMINISTIC_REPAIRED",
        ["outer_commentary"],
    )


def test_extra_closers_are_repaired_without_discarding_another_document():
    value, quality, rules = parse_json_with_quality('{"quote":"原文中的} ]不改"}]}')
    assert value["quote"] == "原文中的} ]不改"
    assert quality == "DETERMINISTIC_REPAIRED" and rules == ["extra_closing_delimiters"]
    for text in ('{"ok":true}{"other":1}', '{"ok":true},"other":1}', '{"ok":true}}}}'):
        with pytest.raises(AIProviderError):
            parse_json_with_quality(text)


def test_v2_map_accepts_absent_empty_auxiliary_collections_but_checks_core_arrays():
    from zhijian.ai.structured_output import validate_structured_output

    metadata = {}
    validate_structured_output('{"entities":[],"claims":[]}', "GROUND_MAP", metadata)
    assert metadata["schema_defaults"] == ["content_units", "relations", "warnings"]
    with pytest.raises(AIProviderError):
        validate_structured_output('{"entities":{},"claims":[]}', "GROUND_MAP")
    with pytest.raises(AIProviderError):
        validate_structured_output('{"entities":[]}', "GROUND_MAP")


def test_local_map_sends_mandatory_native_schema(app_and_session, monkeypatch):
    requests = []

    def post(_url, **kwargs):
        requests.append(kwargs["json"])
        return httpx.Response(
            200,
            request=httpx.Request("POST", _url),
            json={
                "message": {
                    "content": '{"content_units":[],"entities":[],"relations":[],"claims":[],"warnings":[]}'
                },
                "done": True,
                "done_reason": "stop",
            },
        )

    monkeypatch.setattr("zhijian.providers.llm._post", post)
    provider = OllamaProvider("http://local.fixture")
    with app_and_session[1]() as db:
        AIWorkloadGateway().execute_cached_json(
            db,
            job=None,
            stage="GROUND_MAP",
            capability="LLM",
            provider=provider,
            provider_name="ollama",
            model="qwen3.5:9b",
            messages=[{"role": "user", "content": "Return JSON."}],
            semantic_options={},
            cache_enabled=False,
            force_regenerate=True,
        )
    assert requests[0]["format"]["required"] == [
        "content_units",
        "entities",
        "relations",
        "claims",
        "warnings",
    ]
    assert requests[0]["keep_alive"] == 0


def test_cache_is_scoped_and_replay_reads_canonical_result(app_and_session):
    values = segments()
    compiler = compile_request("GROUND_MAP", request(values), values, "snapshot-a")

    class Provider:
        calls = 0

        def generate_json(self, messages, *, model):
            self.calls += 1
            return LLMResult(
                '{"section_facts":[],"places":[{"segment_ids":["s2"],"quote":"最后一段推荐水陆庵。"}],"warnings":[]}',
                "mock",
                model,
                {},
            )

    provider = Provider()
    with app_and_session[1]() as db:
        arguments = dict(
            job=None,
            stage="GROUND_MAP",
            capability="LLM",
            provider=provider,
            provider_name="mock",
            model="mock-model",
            messages=compiler.messages,
            semantic_options={},
            compiled_request=compiler,
            cache_enabled=True,
            force_regenerate=False,
        )
        first = AIWorkloadGateway().execute_cached_json(db, **arguments)
        second = AIWorkloadGateway().execute_cached_json(db, **arguments)
        assert provider.calls == 1 and first.content == second.content
        assert second.metadata["execution_path"] == "CACHE_HIT"
        assert db.scalar(select(AICacheEntry)).result_json["metadata"]["canonical_decoded"]
        arguments["force_regenerate"] = True
        AIWorkloadGateway().execute_cached_json(db, **arguments)
        assert provider.calls == 2
    key_args = dict(
        stage="GROUND_MAP", capability="LLM", provider="mock", model="mock-model", messages=compiler.messages
    )
    other_values = segments("snapshot-b")
    other = compile_request("GROUND_MAP", request(other_values), other_values, "snapshot-b")
    assert compiler.messages == other.messages
    assert cache_key(**key_args, semantic_options=compiler.identity) != cache_key(
        **key_args, semantic_options=other.identity
    )


def test_deadline_is_rechecked_after_queue_and_timeout_is_not_retried(monkeypatch, app_and_session):
    clock = [100.0]
    monkeypatch.setattr("zhijian.ai.gateway.perf_counter", lambda: clock[0])

    class Queue:
        def run(self, _, call, *, cancel_check):
            clock[0] = 102.0
            cancel_check()
            return call()

    monkeypatch.setattr("zhijian.ai.gateway.local_ai_resource_manager", Queue())

    class Provider:
        name = "ollama"

        def generate_json(self, *args, **kwargs):
            pytest.fail("expired waiter must never dispatch")

    with app_and_session[1]() as db, pytest.raises(AIProviderError, match="时限"):
        AIWorkloadGateway().execute_cached_json(
            db,
            job=None,
            stage="GROUND_MAP",
            capability="LLM",
            provider=Provider(),
            provider_name="ollama",
            model="m",
            messages=[],
            semantic_options={},
            cache_enabled=False,
            force_regenerate=False,
            stage_deadline=101.0,
        )

    class Timeout:
        calls = 0

        def generate_json(self, *args, **kwargs):
            self.calls += 1
            raise httpx.ReadTimeout("unknown upstream execution")

    primary = Timeout()
    fallback = FallbackLLMProvider(
        primary, "m", None, None, primary_reliability=ModelReliabilityPolicy("STANDARD", retry_count=2)
    )
    with pytest.raises(AIProviderError):
        fallback.generate_json([], model="m")
    assert primary.calls == 1


def test_business_smoke_and_stale_results_do_not_prove_business_quality():
    value = {"model": "m", "probe_results": {"STRUCTURED_EXTRACTION": "PASS", "FORMAT_SMOKE": "PASS"}}
    assert business_probe_status(value, "STRUCTURED_EXTRACTION") == "NOT_TESTED"
    value["business_assessments"] = business_assessments("m", {"STRUCTURED_EXTRACTION": "PASS"})
    assert business_probe_status(value, "STRUCTURED_EXTRACTION") == "PASS"
    value["business_assessments"][0]["tested_at"] = (utc_now() - timedelta(days=31)).isoformat()
    assert business_probe_status(value, "STRUCTURED_EXTRACTION") == "NOT_TESTED"


def test_model_json_repair_requires_explicit_opt_in():
    from zhijian.ai.reliability import resolve_reliability_policy

    for mode in ("STANDARD", "GUARDED", "FREE_TIER"):
        assert resolve_reliability_policy({"reliability_mode": mode}).json_retry_count == 0
        assert (
            resolve_reliability_policy({"reliability_mode": mode, "json_retry_count": 1}).json_retry_count
            == 1
        )


def test_runtime_metadata_is_allowlisted_and_unload_is_bounded(monkeypatch):
    assert safe_runtime_metadata(
        {
            "prompt": "secret",
            "queue_ms": 25,
            "adapter_ms": -1,
            "actual_model": "m",
            "request_id": "bad secret",
            "total_ms": True,
        }
    ) == {"queue_ms": 25, "actual_model": "m"}
    calls = []

    def post(url, **kwargs):
        calls.append(kwargs)
        return httpx.Response(200, request=httpx.Request("POST", url), json={"done": True})

    monkeypatch.setattr(
        "zhijian.providers.llm._post", lambda *a, **k: (_ for _ in ()).throw(JobCancelled("cancel"))
    )
    monkeypatch.setattr(httpx, "post", post)
    monkeypatch.setattr(
        httpx,
        "get",
        lambda url, **k: httpx.Response(200, request=httpx.Request("GET", url), json={"models": []}),
    )
    with pytest.raises(JobCancelled) as exc:
        OllamaProvider("http://127.0.0.1:11434").generate_json([], model="m")
    assert exc.value.upstream_cleanup == {"state": "UNLOADED", "process_exit": "NOT_VERIFIED"}
    assert len(calls) == 1 and calls[0]["json"] == {"model": "m", "keep_alive": 0}
    assert calls[0]["timeout"] == 3


def test_evidence_trace_rejects_cross_snapshot_empty_quote_and_unknown_ids():
    values = segments()
    assert evidence_trace(values, [values[0].id], "10月", "snapshot-a")["valid"]
    assert not evidence_trace(values, [values[0].id], "10月", "snapshot-b")["valid"]
    assert not evidence_trace(values, [values[0].id], "", "snapshot-a")["valid"]
    assert not evidence_trace(values, ["missing"], "10月", "snapshot-a")["valid"]


def test_all_frozen_cases_have_lossless_synthetic_request_coverage():
    from pathlib import Path

    from zhijian.ai.request_benchmark import evaluate_request_optimization

    path = Path(__file__).parents[2] / "dev docs/benchmark/video-semantic-poi-golden-v1.json"
    result = evaluate_request_optimization(json.loads(path.read_text()))
    assert len(result["rows"]) == 18
    assert result["offline_gate"] and result["provider_calls"] == 0
    assert not result["production_proven"]
    assert result["candidate_json_bytes"] < result["baseline_json_bytes"]
    assert all(
        row["reported_input_tokens"] is None and row["model_quality"] == "NOT_VERIFIED"
        for row in result["rows"]
    )


def test_attempt_transition_is_monotonic_and_terminal_is_immutable(app_and_session):
    from zhijian.core.config import Settings
    from zhijian.db.models import ExternalCallAudit
    from zhijian.services.model_attempts import (
        advance_model_attempt,
        begin_model_attempt,
        finish_model_attempt,
    )

    with app_and_session[1]() as db:
        attempt_id = begin_model_attempt(
            db, Settings(_env_file=None), None, provider="mock", operation="test", request_meta={}
        )
        assert not advance_model_attempt(db, attempt_id, "VALIDATING")
        assert advance_model_attempt(db, attempt_id, "DISPATCHED")
        assert advance_model_attempt(db, attempt_id, "DISPATCHED")
        assert not advance_model_attempt(db, attempt_id, "QUEUED")
        assert advance_model_attempt(db, attempt_id, "VALIDATING")
        assert finish_model_attempt(
            db,
            None,
            attempt_id,
            status="COMPLETED",
            duration_ms=5,
            response_meta={},
            request_meta_updates={},
            error_code=None,
            error_message=None,
        )
        assert not advance_model_attempt(db, attempt_id, "DISPATCHED")
        assert not finish_model_attempt(
            db,
            None,
            attempt_id,
            status="FAILED",
            duration_ms=6,
            response_meta={},
            request_meta_updates={},
            error_code="late",
            error_message=None,
        )
        assert db.get(ExternalCallAudit, attempt_id).status == "COMPLETED"
