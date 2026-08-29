from types import SimpleNamespace

from deploy.macos import manage


def test_bootout_waits_until_launchd_label_disappears(monkeypatch) -> None:
    results = iter((0, 0, 1))
    calls: list[tuple[str, ...]] = []

    def fake_launchctl(*arguments: str, check: bool = True):
        calls.append(arguments)
        return SimpleNamespace(returncode=next(results))

    monkeypatch.setattr(manage, "launchctl", fake_launchctl)
    monkeypatch.setattr(manage.time, "sleep", lambda _: None)

    manage._bootout_and_wait("gui/501", "cn.zhijian.api")

    assert calls == [
        ("bootout", "gui/501/cn.zhijian.api"),
        ("print", "gui/501/cn.zhijian.api"),
        ("print", "gui/501/cn.zhijian.api"),
    ]


def test_ensure_ollama_models_link_is_persistent_and_idempotent(tmp_path, monkeypatch) -> None:
    model_store = tmp_path / "external-models"
    (model_store / "blobs").mkdir(parents=True)
    (model_store / "manifests").mkdir()
    default_store = tmp_path / "home" / ".ollama" / "models"
    default_store.mkdir(parents=True)
    (default_store / ".DS_Store").write_text("old")
    monkeypatch.setattr(manage, "OLLAMA_MODELS", model_store)
    monkeypatch.setattr(manage, "DEFAULT_OLLAMA_MODELS", default_store)

    manage.ensure_ollama_models_link()
    manage.ensure_ollama_models_link()

    assert default_store.is_symlink()
    assert default_store.resolve() == model_store.resolve()
    backups = list(default_store.parent.glob("models.before-zhijian-*"))
    assert len(backups) == 1
    assert (backups[0] / ".DS_Store").read_text() == "old"


def test_ensure_ollama_models_link_rejects_missing_store(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(manage, "OLLAMA_MODELS", tmp_path / "missing")
    monkeypatch.setattr(manage, "DEFAULT_OLLAMA_MODELS", tmp_path / "default")

    try:
        manage.ensure_ollama_models_link()
    except SystemExit as exc:
        assert "模型目录无效" in str(exc)
    else:
        raise AssertionError("missing Ollama model store must fail installation")
