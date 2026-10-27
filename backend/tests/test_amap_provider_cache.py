import os
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

from zhijian.core.config import Settings
from zhijian.providers.amap import AMapPOIProvider


@pytest.fixture(autouse=True)
def isolate_amap_runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "zhijian.providers.amap.get_settings", lambda: Settings(_env_file=None, data_dir=tmp_path)
    )
    AMapPOIProvider._cache.clear()
    AMapPOIProvider._inflight.clear()


def test_amap_provider_coalesces_duplicate_query_without_sharing_mutation(monkeypatch) -> None:
    calls = 0

    class Response:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "status": "1",
                "pois": [{"id": "poi-1", "name": "大理古城", "location": "100,20"}],
            }

    def get(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return Response()

    AMapPOIProvider._cache.clear()
    monkeypatch.setattr("zhijian.providers.amap.httpx.get", get)
    provider = AMapPOIProvider("fixture")
    first = provider.search("大理古城", "大理")
    first[0].score = 99
    second = provider.search("大理古城", "大理")

    assert calls == provider.request_count == 1
    assert provider.cache_hit_count == 1
    assert second[0].score == 0


@pytest.mark.parametrize("http_status,info", [(200, "CUQPS_HAS_EXCEEDED_THE_LIMIT"), (429, "")])
def test_amap_qps_failure_cools_down_without_retry_or_caching(monkeypatch, http_status, info):
    clock = [100.0]
    starts = []

    def get(*args, **kwargs):
        starts.append(clock[0])
        return httpx.Response(
            http_status,
            json={"status": "0", "info": info},
            request=httpx.Request("GET", "https://restapi.amap.com/v5/place/text?key=fixture-secret"),
        )

    monkeypatch.setattr("zhijian.providers.amap.monotonic", lambda: clock[0])
    monkeypatch.setattr("zhijian.providers.amap.sleep", lambda delay: clock.__setitem__(0, clock[0] + delay))
    monkeypatch.setattr("zhijian.providers.amap.httpx.get", get)
    provider = AMapPOIProvider("fixture")
    for _ in range(2):
        with pytest.raises(RuntimeError) as error:
            provider.search("限流测试")
        assert "fixture-secret" not in str(error.value)
    assert starts == [100.0, 105.0]
    assert provider.request_count == 2
    assert provider.cache_hit_count == 0


def test_amap_cache_isolated_by_credential(monkeypatch):
    monkeypatch.setattr(AMapPOIProvider, "_request_interval_seconds", 0)

    def get(*args, **kwargs):
        key = kwargs["params"]["key"]
        return httpx.Response(
            200,
            json={"status": "1", "pois": [{"id": key, "name": "同一地点", "location": "100,20"}]},
            request=httpx.Request("GET", "https://restapi.amap.com/v5/place/text"),
        )

    monkeypatch.setattr("zhijian.providers.amap.httpx.get", get)
    first, second = AMapPOIProvider("first-secret"), AMapPOIProvider("second-secret")
    assert first.search("同一地点")[0].provider_id == "first-secret"
    assert second.search("同一地点")[0].provider_id == "second-secret"
    assert first.request_count == second.request_count == 1
    assert all("secret" not in key for key in AMapPOIProvider._cache)


def test_amap_requests_are_paced_across_processes(tmp_path):
    script = """
import sys
from time import monotonic
import httpx
import zhijian.providers.amap as amap
from zhijian.core.config import Settings
amap.get_settings = lambda: Settings(_env_file=None, data_dir=sys.argv[1])
amap.AMapPOIProvider._request_interval_seconds = 0.1
def get(*args, **kwargs):
    print(monotonic(), flush=True)
    return httpx.Response(200, json={'status': '1', 'pois': []}, request=httpx.Request('GET', 'https://restapi.amap.com/v5/place/text'))
amap.httpx.get = get
p = amap.AMapPOIProvider(sys.argv[2])
p.search('测试')
p.around(100, 20)
"""
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    processes = [
        subprocess.Popen(
            [sys.executable, "-c", script, str(tmp_path), key],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        for key in ("account-key-1", "account-key-2")
    ]
    starts = []
    try:
        for process in processes:
            stdout, stderr = process.communicate(timeout=10)
            assert process.returncode == 0, stderr
            starts.extend(float(line) for line in stdout.splitlines())
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.wait()
    starts.sort()
    assert len(starts) == 4
    assert all(right - left >= 0.09 for left, right in zip(starts, starts[1:], strict=False))
