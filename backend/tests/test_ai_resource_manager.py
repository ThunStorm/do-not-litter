from zhijian.ai.resource_manager import LocalAIResourceManager


def test_local_ai_resource_manager_marks_and_releases_heavy_work() -> None:
    manager = LocalAIResourceManager()
    assert manager.run("ASR", lambda: manager.active_kind) == "ASR"
    assert manager.active_kind is None
