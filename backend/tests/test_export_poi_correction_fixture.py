from __future__ import annotations

import importlib.util
from pathlib import Path

from zhijian.db.models import PlaceMention, Source, VideoAsset


def _exporter():
    path = Path(__file__).parents[2] / "scripts" / "export_poi_correction_fixture.py"
    spec = importlib.util.spec_from_file_location("export_poi_correction_fixture", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_export_poi_correction_fixture_only_exports_manual_confirmations(app_and_session) -> None:
    _, factory = app_and_session
    with factory() as db:
        source = Source(source_type="URL", locator="https://example.test/corrections")
        db.add(source)
        db.flush()
        asset = VideoAsset(source_id=source.id, canonical_url=source.locator)
        db.add(asset)
        db.flush()
        db.add_all(
            [
                PlaceMention(
                    video_asset_id=asset.id,
                    name="翠湖公园",
                    resolution_status="CONFIRMED",
                    metadata_json={
                        "confirmation_origin": "MANUAL_CONFIRMED",
                        "poi_id": "cuihu",
                        "poi_candidates": [
                            {
                                "provider_id": "cuihu",
                                "name": "翠湖公园",
                                "city": "昆明市",
                                "longitude": 102.7,
                                "latitude": 25.05,
                            }
                        ],
                    },
                ),
                PlaceMention(
                    video_asset_id=asset.id,
                    name="自动确认",
                    resolution_status="CONFIRMED",
                    metadata_json={"confirmation_origin": "AUTO_STRONG"},
                ),
            ]
        )
        db.commit()

        rows = _exporter().export_corrections(db)

    assert len(rows) == 1
    assert rows[0]["expected"] == {"candidate_id": "cuihu", "status": "CONFIRMED"}
    assert rows[0]["candidates"][0]["city"] == "昆明市"
