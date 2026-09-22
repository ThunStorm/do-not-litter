from zhijian.ai.runtime_hints import read_runtime_hint, tighten_runtime_hint


def test_runtime_hints_only_tighten_and_are_model_scoped(app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        first = tighten_runtime_hint(
            db, "GROUND_MAP", "model-a", safe_max_chars=6000, safe_max_segments=64
        )
        tighter = tighten_runtime_hint(
            db, "GROUND_MAP", "model-a", safe_max_chars=3000, safe_max_segments=32
        )
        ignored_relax = tighten_runtime_hint(
            db, "GROUND_MAP", "model-a", safe_max_chars=5000, safe_max_segments=48
        )

        assert first == {"safe_max_chars": 6000, "safe_max_segments": 64}
        assert tighter == ignored_relax == {"safe_max_chars": 3000, "safe_max_segments": 32}
        assert read_runtime_hint(db, "GROUND_MAP", "model-b") == {}
