from zhijian.ai.capabilities import AICapability
from zhijian.ai.domain_context import DOMAIN_PACK_PREFIX, domain_context_messages
from zhijian.db.models import Setting


def _pack() -> dict:
    return {
        "id": "travel-cn",
        "name": "中国旅行",
        "version": "v1",
        "glossary": {"早市": "清晨营业的市场"},
        "aliases": {"钟楼": ["鼓楼钟楼"]},
        "rules": ["保留地点歧义，不猜测坐标"],
        "examples": [{"input": "早市", "output": "市场候选"}],
        "prompt_supplement": "优先保留地方称呼。",
        "allowed_capabilities": ["ENTITY_EXTRACTION"],
    }


def test_domain_pack_api_and_context_capability_filter(client, app_and_session) -> None:
    _, factory = app_and_session
    created = client.post("/api/ai/domain-packs", json=_pack())
    assert created.status_code == 200
    assert client.get("/api/ai/domain-packs").json()[0]["id"] == "travel-cn"
    with factory() as db:
        messages, versions = domain_context_messages(
            db, ["travel-cn"], AICapability.ENTITY_EXTRACTION
        )
        assert "早市" in messages[0]["content"] and versions == {"travel-cn": "v1"}
        blocked, _ = domain_context_messages(db, ["travel-cn"], AICapability.GLOBAL_SYNTHESIS)
        assert blocked == []
        assert db.get(Setting, f"{DOMAIN_PACK_PREFIX}travel-cn") is not None


def test_vision_stage_rejects_text_only_profile_and_accepts_image_profile(client) -> None:
    def profile(name: str, modalities: list[str]) -> dict:
        return {
            "name": name,
            "provider": "Ollama",
            "base_url": "http://127.0.0.1:11434",
            "model": name,
            "location": "LOCAL",
            "modalities": modalities,
        }

    text = client.post("/api/settings/model-profiles", json=profile("text", ["text"])).json()["id"]
    image = client.post("/api/settings/model-profiles", json=profile("image", ["text", "image"])).json()["id"]
    payload = {
        "stage": "SCREENSHOT_UNDERSTANDING",
        "capability": "SCREENSHOT_UNDERSTANDING",
        "execution_mode": "LOCAL_ONLY",
        "local_profile_id": text,
    }
    assert client.put("/api/ai/stage-policies/SCREENSHOT_UNDERSTANDING", json=payload).status_code == 422
    payload["local_profile_id"] = image
    saved = client.put("/api/ai/stage-policies/SCREENSHOT_UNDERSTANDING", json=payload)
    assert saved.status_code == 200
