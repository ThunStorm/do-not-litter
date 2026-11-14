import copy
import json

import pytest

from zhijian.ai.gateway import AIWorkloadGateway
from zhijian.ai.json_recovery import json_error_details
from zhijian.ai.reliability import AIProviderError, ModelReliabilityPolicy
from zhijian.ai.structured_output import validate_structured_output
from zhijian.db.models import AICacheEntry
from zhijian.providers.llm import FallbackLLMProvider, LLMResult


def payload():
    return {
        "entities": [{"recommendation_evidence": {"statements": [{"supersedes": []}]}}],
        "claims": [],
    }


@pytest.mark.parametrize("bad", [None, "", {}])
@pytest.mark.parametrize(
    "collection,field",
    [
        ("entities", "segment_ids"),
        ("entities", "temporal_applications"),
        ("claims", "subject_entity_ids"),
        ("content_units", "anchor_entity_ids"),
        ("section_facts", "supporting_quotes"),
        ("section_facts", "key_points"),
        ("places", "segment_ids"),
        ("relations", "segment_ids"),
    ],
)
def test_ground_map_rejects_wrong_list_types_with_safe_field_path(collection, field, bad):
    data = payload()
    data[collection] = [{field: bad}]
    with pytest.raises(AIProviderError) as caught:
        validate_structured_output(json.dumps(data), "GROUND_MAP")
    detail = json_error_details(json.dumps(data), caught.value)
    assert caught.value.code == "AI_PROVIDER_SCHEMA_INVALID"
    assert detail["schema_error"] == {"kind": "INVALID_LIST", "path": f"$.{collection}[0].{field}"}


@pytest.mark.parametrize("field", ["statements", "supersedes"])
def test_nested_recommendation_null_is_schema_error(field):
    data = payload()
    evidence = data["entities"][0]["recommendation_evidence"]
    if field == "statements":
        evidence[field] = None
    else:
        evidence["statements"][0][field] = None
    with pytest.raises(AIProviderError) as caught:
        validate_structured_output(json.dumps(data), "GROUND_MAP")
    assert caught.value.schema_diagnostic["path"].endswith("." + field)


@pytest.mark.parametrize(
    "retries,has_backup,max_attempts,expected",
    [
        (0, True, None, ["primary", "fallback"]),
        (1, True, None, ["primary", "primary", "fallback"]),
        (0, False, None, ["primary"]),
        (0, True, 1, ["primary"]),
    ],
)
def test_null_recovery_uses_original_evidence_and_bounded_backup(
    app_and_session, retries, has_backup, max_attempts, expected
):
    calls = []
    attempts = []
    original = [{"role": "user", "content": "完整原始证据"}]

    class Provider:
        def __init__(self, name):
            self.name = name

        def generate_json(self, messages, **kwargs):
            calls.append(self.name)
            assert messages[-1]["content"].endswith(original[-1]["content"])
            data = payload()
            if self.name == "primary":
                data["entities"][0]["recommendation_evidence"]["statements"][0]["supersedes"] = None
            return LLMResult(json.dumps(data), self.name, self.name, {})

    provider = FallbackLLMProvider(
        Provider("primary"),
        "primary",
        Provider("fallback") if has_backup else None,
        "fallback" if has_backup else None,
        primary_reliability=ModelReliabilityPolicy("DIRECT", json_retry_count=retries),
        fallback_reliability=ModelReliabilityPolicy("DIRECT"),
        sleeper=lambda _: None,
        max_attempts=max_attempts,
        on_attempt=lambda *args: attempts.append(args),
    )
    with app_and_session[1]() as db:
        kwargs = dict(
            job=None,
            stage="GROUND_MAP",
            capability="LLM",
            provider=provider,
            provider_name="primary",
            model="primary",
            messages=copy.deepcopy(original),
            semantic_options={},
            cache_enabled=True,
            force_regenerate=False,
        )
        if expected[-1] == "fallback":
            result = AIWorkloadGateway().execute_cached_json(db, **kwargs)
            assert result.provider == "fallback"
            assert db.query(AICacheEntry).count() == 1
            # Cache read validates again, without another primary or fallback request.
            AIWorkloadGateway().execute_cached_json(db, **kwargs)
        else:
            with pytest.raises(AIProviderError):
                AIWorkloadGateway().execute_cached_json(db, **kwargs)
            assert db.query(AICacheEntry).count() == 0
    assert calls == expected
    assert attempts[0][6].code == "AI_PROVIDER_SCHEMA_INVALID"


@pytest.mark.parametrize(
    "retries,has_backup,max_attempts,expected",
    [
        (1, False, None, ["primary", "primary"]),
        (0, True, None, ["primary", "fallback"]),
        (1, True, 1, ["primary"]),
        (0, False, None, ["primary"]),
    ],
)
def test_root_array_reuses_recovery_budget_and_does_not_poison_cache(
    app_and_session, retries, has_backup, max_attempts, expected
):
    calls = []
    original = [{"role": "user", "content": "原始逐字证据，不猜ID"}]

    class Provider:
        def __init__(self, name):
            self.name = name

        def generate_json(self, messages, **kwargs):
            calls.append(self.name)
            assert messages[-1]["content"].endswith(original[-1]["content"])
            if self.name == "fallback":
                assert messages == original
            valid = self.name == "fallback" or len(calls) > 1
            return LLMResult('{"sections":[]}' if valid else '[{"sections":[]}]',
                             self.name, self.name, {})

    provider = FallbackLLMProvider(
        Provider("primary"), "primary",
        Provider("fallback") if has_backup else None, "fallback" if has_backup else None,
        primary_reliability=ModelReliabilityPolicy("DIRECT", json_retry_count=retries),
        fallback_reliability=ModelReliabilityPolicy("DIRECT"),
        sleeper=lambda _: None, max_attempts=max_attempts,
    )
    with app_and_session[1]() as db:
        kwargs = dict(
            job=None, stage="NOTE_REDUCE", capability="LLM", provider=provider,
            provider_name="primary", model="primary", messages=copy.deepcopy(original),
            semantic_options={}, cache_enabled=True, force_regenerate=False,
        )
        gateway = AIWorkloadGateway()
        if len(expected) > 1:
            result = gateway.execute_cached_json(db, **kwargs)
            assert json.loads(result.content) == {"sections": []}
            assert db.query(AICacheEntry).count() == 1
            gateway.execute_cached_json(db, **kwargs)
        else:
            with pytest.raises(AIProviderError):
                gateway.execute_cached_json(db, **kwargs)
            assert db.query(AICacheEntry).count() == 0
    assert calls == expected
