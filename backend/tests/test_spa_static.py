from fastapi import FastAPI
from fastapi.testclient import TestClient

from zhijian.main import SPAStaticFiles


def test_spa_history_fallback_preserves_asset_404(tmp_path) -> None:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<h1>至简</h1>", encoding="utf-8")
    app = FastAPI()
    app.mount("/", SPAStaticFiles(directory=tmp_path, html=True))

    with TestClient(app) as client:
        assert client.get("/map").status_code == 200
        assert "至简" in client.get("/places/example").text
        assert client.get("/assets/missing.js").status_code == 404
