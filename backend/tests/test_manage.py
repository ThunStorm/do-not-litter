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
