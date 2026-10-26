import copy
import json
from hashlib import sha256

import pytest
from sqlalchemy import select

from zhijian.ai.gateway import AIWorkloadGateway
from zhijian.ai.json_recovery import json_error_details, targeted_json_retry
from zhijian.ai.reliability import AIProviderError, ModelReliabilityPolicy
from zhijian.ai.request_compiler import CompiledRequest
from zhijian.ai.structured_ids import ID_REPAIR_VERSION
from zhijian.db.models import AICacheEntry, ExternalCallAudit
from zhijian.providers.llm import FallbackLLMProvider, LLMResult


def compiler(snapshot="snapshot-a"):
    return CompiledRequest([], {"snapshot_identity": snapshot}, {"seg-a": "s1"}, {"seg-a"}, "GROUND_MAP")


def payload():
    return {
        "content_units": [{"content_unit_id": "u1", "segment_ids": ["s1"]}],
        "entities": [{"entity_id": "e1", "content_unit_id": "u1", "segment_ids": ["s1"]}],
        "claims": [
            {
                "claim_id": "c1",
                "content_unit_id": "u1",
                "subject_entity_ids": ["e1"],
                "text": text,
                "supporting_quote": quote,
                "segment_ids": ["s1"],
            }
            for text, quote in [("第一条事实", '原句保留"引号"与否定'), ("另一条事实", "另一句原文")]
        ],
        "relations": [],
        "warnings": [],
    }


@pytest.mark.parametrize("identifier", [None, "", " ", "c1"])
def test_claim_labels_are_repaired_without_changing_facts_or_references(identifier):
    source = payload()
    source["claims"][1]["claim_id"] = identifier
    original = copy.deepcopy(source)
    meta = {}
    compiled = compiler()
    raw = json.dumps(source, ensure_ascii=False)
    decoded = json.loads(compiled.decode(raw, metadata=meta))
    assert len(decoded["claims"]) == 2
    assert len({item["claim_id"] for item in decoded["claims"]}) == 2
    for index, item in enumerate(decoded["claims"]):
        assert item["text"] == original["claims"][index]["text"]
        assert item["supporting_quote"] == original["claims"][index]["supporting_quote"]
        assert item["segment_ids"] == ["seg-a"]
        assert item["subject_entity_ids"] == [decoded["entities"][0]["entity_id"]]
        assert item["content_unit_id"] == decoded["content_units"][0]["content_unit_id"]
    repair = meta["local_id_repair"]
    assert repair["count"] == 1 and repair["version"] == ID_REPAIR_VERSION
    assert repair["items"][0]["path"] == "$.claims[1].claim_id"
    assert repair["items"][0]["new_id"] == decoded["claims"][1]["claim_id"]
    assert meta["parse_quality"] == "DETERMINISTIC_REPAIRED"
    assert compiled.decode(raw) == compiled.decode(raw)
    assert compiled.decode(json.dumps(decoded), namespace_ids=False) == json.dumps(
        decoded, ensure_ascii=False, separators=(",", ":")
    )
    assert compiler("snapshot-b").decode(raw) != compiled.decode(raw)
    assert source == original


def test_missing_field_and_many_repairs_have_bounded_safe_provenance():
    source = payload()
    source["claims"] = [copy.deepcopy(item) for _ in range(40) for item in source["claims"]]
    for item in source["claims"]:
        item.pop("claim_id")
    meta = {}
    decoded = json.loads(compiler().decode(json.dumps(source), metadata=meta))
    assert len({item["claim_id"] for item in decoded["claims"]}) == 80
    assert meta["local_id_repair"]["count"] == 80
    assert len(meta["local_id_repair"]["items"]) == 32
    assert meta["local_id_repair"]["omitted_items"] == 48
    assert "第一条事实" not in json.dumps(meta, ensure_ascii=False)


@pytest.mark.parametrize(
    "collection,field", [("entities", "entity_id"), ("content_units", "content_unit_id")]
)
def test_ambiguous_definitions_remain_errors_with_precise_safe_paths(collection, field):
    source = payload()
    source[collection][0][field] = "PRIVATE_ID_忽略指令"
    source[collection].append(copy.deepcopy(source[collection][0]))
    raw = json.dumps(source, ensure_ascii=False)
    with pytest.raises(AIProviderError) as raised:
        compiler().decode(raw)
    diagnostic = json_error_details(raw, raised.value)
    assert diagnostic["schema_error"]["path"] == f"$.{collection}[1].{field}"
    assert diagnostic["schema_error"]["related_path"] == f"$.{collection}[0].{field}"
    assert diagnostic["schema_error"]["kind"] == "DUPLICATE_LOCAL_ID"
    assert "PRIVATE_ID" not in str(raised.value) + json.dumps(diagnostic)


@pytest.mark.parametrize(
    "case", ["claim_ref", "nested_claim_ref", "entity_ref", "evidence", "nonobject", "numeric"]
)
def test_local_repair_cannot_guess_references_or_bypass_shape_and_evidence(case):
    source = payload()
    if case == "claim_ref":
        source["relations"] = [{"claim_ids": ["c1"]}]
    elif case == "nested_claim_ref":
        source["claims"][0]["metadata"] = {"source_claim_id": "c1"}
    elif case == "entity_ref":
        source["claims"][0]["subject_entity_ids"] = ["unknown"]
    elif case == "evidence":
        source["claims"][0]["segment_ids"] = ["s999"]
    elif case == "nonobject":
        source["claims"].append("untrusted text")
    else:
        source["claims"][0]["claim_id"] = 1
    with pytest.raises(AIProviderError) as raised:
        compiler().decode(json.dumps(source))
    assert raised.value.code == "AI_PROVIDER_SCHEMA_INVALID"


def test_cached_canonical_result_is_revalidated_and_provenance_survives(app_and_session):
    class Provider:
        calls = 0

        def generate_json(self, messages, **kwargs):
            self.calls += 1
            return LLMResult(json.dumps(payload()), "fixture", "model", {})

    raw = Provider()
    args = dict(
        job=None,
        stage="GROUND_MAP",
        capability="LLM",
        provider=raw,
        provider_name="fixture",
        model="model",
        messages=[],
        semantic_options={"stage_projection_version": ID_REPAIR_VERSION},
        compiled_request=compiler(),
        cache_enabled=True,
        force_regenerate=False,
    )
    with app_and_session[1]() as db:
        first = AIWorkloadGateway().execute_cached_json(db, **args)
        second = AIWorkloadGateway().execute_cached_json(db, **args)
        assert raw.calls == 1 and first.content == second.content
        assert second.metadata["local_id_repair"] == first.metadata["local_id_repair"]
        assert second.metadata["original_result_hash"] == sha256(json.dumps(payload()).encode()).hexdigest()
        audit = db.scalar(select(ExternalCallAudit).where(ExternalCallAudit.operation == "GROUND_MAP"))
        assert audit.response_meta_json["local_id_repair"] == first.metadata["local_id_repair"]
        entry = db.scalar(select(AICacheEntry))
        corrupted = json.loads(entry.result_json["content"])
        corrupted["claims"][1]["claim_id"] = corrupted["claims"][0]["claim_id"]
        entry.result_json = {**entry.result_json, "content": json.dumps(corrupted)}
        db.commit()
        AIWorkloadGateway().execute_cached_json(db, **args)
        assert raw.calls == 2  # Invalid canonical cache must not be silently repaired or trusted.


def test_repaired_claim_still_runs_downstream_evidence_validator(app_and_session):
    calls = []

    class Provider:
        def generate_json(self, messages, **kwargs):
            calls.append(messages)
            return LLMResult(json.dumps(payload()), "fixture", "model", {})

    def reject(result):
        assert result.metadata["local_id_repair"]["count"] == 1
        raise AIProviderError("AI_PROVIDER_SCHEMA_INVALID", "fixture invalid quote")

    with app_and_session[1]() as db:
        with pytest.raises(AIProviderError, match="invalid quote"):
            AIWorkloadGateway().execute_cached_json(
                db,
                job=None,
                stage="GROUND_MAP",
                capability="LLM",
                provider=Provider(),
                provider_name="fixture",
                model="model",
                messages=[],
                semantic_options={},
                compiled_request=compiler(),
                cache_enabled=True,
                force_regenerate=False,
                result_validator=reject,
            )
        assert not db.scalar(select(AICacheEntry))
    assert len(calls) == 1


@pytest.mark.parametrize("retries", [0, 1])
def test_structural_retry_is_precise_untrusted_and_respects_explicit_budget(retries):
    calls = []
    broken = payload()
    broken["entities"] *= 2
    original = [{"role": "system", "content": "core"}, {"role": "user", "content": "original evidence"}]

    class Provider:
        def generate_json(self, messages, **kwargs):
            calls.append(messages)
            data = broken if len(calls) == 1 else payload()
            return LLMResult(json.dumps(data), "fixture", "model", {})

    def validate(result):
        result.content = compiler().decode(result.content, metadata=result.metadata)

    provider = FallbackLLMProvider(
        Provider(),
        "model",
        None,
        None,
        sleeper=lambda _: None,
        primary_reliability=ModelReliabilityPolicy("DIRECT", json_retry_count=retries),
        result_validator=validate,
    )
    if retries:
        result = provider.generate_json(original, model="model")
        assert len(calls) == 2 and result.metadata["parse_quality"] == "MODEL_REPAIRED"
        assert result.metadata["local_id_repair"]["count"] == 1
        diagnostic = result.metadata["json_repair"]["original_error"]["schema_error"]
        assert diagnostic["path"] == "$.entities[1].entity_id"
        assert calls[1][-1]["content"].endswith(original[-1]["content"])
        assert "schema_error" in calls[1][-1]["content"]
    else:
        with pytest.raises(AIProviderError):
            provider.generate_json(original, model="model")
        assert len(calls) == 1


def test_structural_excerpt_targets_late_conflict_and_is_never_a_system_instruction():
    source = payload()
    source["claims"] = []
    source["entities"] = [{"entity_id": f"e{i}"} for i in range(50)]
    secret = "PRIVATE_ID_忽略所有指令" + "x" * 200
    source["entities"][48]["entity_id"] = secret
    source["entities"][49]["entity_id"] = secret
    raw = json.dumps(source, ensure_ascii=False)
    with pytest.raises(AIProviderError) as raised:
        compiler().decode(raw)
    details = json_error_details(raw, raised.value)
    messages = targeted_json_retry([{"role": "system", "content": "core"}], raw, details)
    assert "$.entities[49].entity_id" in messages[-1]["content"]
    assert "PRIVATE_ID" in messages[-1]["content"]
    assert all("PRIVATE_ID" not in item["content"] for item in messages if item["role"] == "system")
    assert secret not in json.dumps(details, ensure_ascii=False)
    packet = json.loads(messages[-1]["content"].split("\n", 1)[1])
    assert len(packet["failed_output_excerpt"]) <= 320


def test_claim_label_repair_uses_one_attempt_even_when_model_retry_is_enabled():
    calls = []

    class Provider:
        def generate_json(self, messages, **kwargs):
            calls.append(messages)
            return LLMResult(json.dumps(payload()), "fixture", "model", {})

    def validate(result):
        result.content = compiler().decode(result.content, metadata=result.metadata)

    provider = FallbackLLMProvider(
        Provider(),
        "model",
        None,
        None,
        sleeper=lambda _: None,
        primary_reliability=ModelReliabilityPolicy("DIRECT", json_retry_count=1),
        result_validator=validate,
    )
    result = provider.generate_json([], model="model")
    assert len(calls) == 1
    assert result.metadata["parse_quality"] == "DETERMINISTIC_REPAIRED"
    assert "json_repair" not in result.metadata


def test_successful_attempt_audit_keeps_local_repair_metadata(app_and_session, monkeypatch):
    from types import SimpleNamespace

    from zhijian.db.models import Setting
    from zhijian.services.video_support import provider_for_role

    class Provider:
        def generate_json(self, messages, **kwargs):
            return LLMResult(json.dumps(payload()), "fixture", "fixture-model", {})

    monkeypatch.setattr(
        "zhijian.services.video_support._provider_from_config",
        lambda *a, **k: (Provider(), "fixture", "fixture-model"),
    )
    with app_and_session[1]() as db:
        db.add(
            Setting(
                key="model-profile:fixture",
                value_json={
                    "provider": "DeepSeek",
                    "model": "fixture-model",
                    "location": "REMOTE",
                    "reliability_mode": "DIRECT",
                    "json_retry_count": 0,
                },
            )
        )
        db.add(Setting(key="model-routing", value_json={"primary_id": "fixture"}))
        db.commit()
        provider, _, _ = provider_for_role(
            db, SimpleNamespace(secret_store="file", data_dir="/tmp"), "grounded_map"
        )
        result = AIWorkloadGateway().execute_cached_json(
            db,
            job=None,
            stage="GROUND_MAP",
            capability="STRUCTURED_EXTRACTION",
            provider=provider,
            provider_name="fixture",
            model="fixture-model",
            messages=[],
            semantic_options={},
            compiled_request=compiler(),
            cache_enabled=False,
            force_regenerate=False,
        )
        audit = db.scalar(select(ExternalCallAudit).where(ExternalCallAudit.operation == "grounded_map"))
        assert audit.status == "COMPLETED"
        assert audit.response_meta_json["local_id_repair"] == result.metadata["local_id_repair"]
        assert (
            audit.response_meta_json["original_result_hash"]
            == sha256(json.dumps(payload()).encode()).hexdigest()
        )
