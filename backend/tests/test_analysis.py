"""Phase 4 feature engineering and anomaly tests."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest

from backend.processing.analyze import run_analysis
from backend.processing.indices import compute_ndvi
from backend.processing.io import read_band, write_feature_raster
from backend.processing.scoring import SignalInput, score_aoi_anomaly
from backend.shared.config import get_settings
from backend.tests.raster_fixtures import write_geotiff


def _clear_caches() -> None:
    get_settings.cache_clear()


def _write_normalized(path: Path, bounds: tuple, seed: int) -> None:
    """Write a normalized-style float raster."""
    write_geotiff(path, bounds, width=64, height=64, seed=seed, value_scale=0.8)
    data, profile = read_band(path)
    data = (data - data.min()) / max(data.max() - data.min(), 1e-6)
    write_feature_raster(path, data.astype(np.float32), profile)


@pytest.fixture
def analysis_env(tmp_path: Path, monkeypatch):
    data = tmp_path / "data"
    registry = data / "registry"
    registry.mkdir(parents=True)
    aois_src = Path(__file__).resolve().parents[2] / "data" / "registry" / "aois.json"
    (registry / "aois.json").write_text(aois_src.read_text(encoding="utf-8"), encoding="utf-8")
    aois = json.loads(aois_src.read_text(encoding="utf-8"))
    bounds = (34.75, 31.2, 34.85, 31.3)
    now = datetime.now(timezone.utc)
    dt1 = (now - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    dt2 = (now - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")

    items = []
    for i, (iid, band, dt) in enumerate(
        [
            ("s2-t1-b04", "B04", dt1),
            ("s2-t1-b08", "B08", dt1),
            ("s2-t2-b04", "B04", dt2),
            ("s2-t2-b08", "B08", dt2),
        ]
    ):
        coll = "sentinel-2-l2a"
        rel = f"raw/{coll}/aoi-levant/{iid}.tif"
        norm = data / "processed" / coll / "aoi-levant" / iid / "normalized.tif"
        _write_normalized(norm, bounds, seed=10 + i)
        items.append(
            {
                "type": "Item",
                "id": iid,
                "collection": coll,
                "properties": {
                    "datetime": dt,
                    "platform": "sentinel-2",
                    "gs:collection": coll,
                    "gs:aoi_id": "aoi-levant",
                    "gs:bands": [band],
                    "eo:cloud_cover": 5,
                },
                "assets": {"data": {"href": rel.replace("\\", "/")}},
                "geometry": aois["aois"][0]["geometry"],
            }
        )

    # SAR disturbance feature
    sar_diff = (
        data
        / "processed"
        / "sentinel-1-grd"
        / "aoi-levant"
        / "disturbance"
        / "s1-t1_to_s1-t2_diff.tif"
    )
    _write_normalized(sar_diff, bounds, seed=99)

    catalog = {"type": "Catalog", "id": "t", "stac_version": "1.0.0", "items": items}
    (registry / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")

    monkeypatch.setenv("DATA_ROOT", str(data))
    monkeypatch.setenv("REGISTRY_PATH", str(registry))
    monkeypatch.setenv("ANOMALY_COMPOSITE_THRESHOLD", "0.3")
    _clear_caches()
    yield data, registry
    _clear_caches()


def test_score_aoi_anomaly_rules():
    report = score_aoi_anomaly(
        "aoi-test",
        "20260501",
        [
            SignalInput("vegetation_change", 0.35, 0.5, 0.15, "veg"),
            SignalInput("surface_disturbance", 0.20, 0.1, 0.20, "sar"),
        ],
        {},
        composite_threshold=0.4,
    )
    assert report.composite_score >= 0
    assert len(report.signals) == 2


def test_run_analysis(analysis_env):
    result = run_analysis(run_id="test-analysis")
    assert result.features_ok >= 4
    ndvi_features = [f for f in result.feature_results if f.feature == "ndvi" and f.status.value == "ok"]
    assert len(ndvi_features) >= 2
    temporal = [f for f in result.feature_results if f.feature == "temporal_ndvi"]
    assert len(temporal) >= 1

    settings = get_settings()
    report_files = list(
        (settings.resolve_data_path("processed/anomalies/aoi-levant")).glob("report_*.json")
    )
    assert len(report_files) >= 1


@pytest.mark.anyio
async def test_api_analysis_run(client, analysis_env):
    _clear_caches()
    r = await client.post("/api/v1/analysis/run", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["features_ok"] >= 1


@pytest.mark.anyio
async def test_api_list_anomalies(client, analysis_env):
    _clear_caches()
    await client.post("/api/v1/analysis/run", json={})
    r = await client.get("/api/v1/analysis/anomalies/aoi-levant")
    assert r.status_code == 200
    assert r.json()["count"] >= 1
