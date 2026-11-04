"""Phase 6 explainability and alerts tests."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.alerts.generate import generate_alerts
from backend.explainability.colormap import apply_colormap, raster_to_heatmap_png
from backend.explainability.confidence import build_confidence_breakdown
from backend.explainability.generate import run_explainability
from backend.explainability.timelines import build_timeline
from backend.shared.config import get_settings
from backend.tests.raster_fixtures import write_geotiff


def _clear_caches() -> None:
    get_settings.cache_clear()


@pytest.fixture
def explainability_env(tmp_path: Path, monkeypatch):
    data = tmp_path / "data"
    registry = data / "registry"
    registry.mkdir(parents=True)
    aois_src = Path(__file__).resolve().parents[2] / "data" / "registry" / "aois.json"
    (registry / "aois.json").write_text(aois_src.read_text(encoding="utf-8"), encoding="utf-8")

    now = datetime.now(timezone.utc)
    date_key = now.strftime("%Y%m%d")
    run_id = "test-run-001"
    bounds = (34.75, 31.2, 34.85, 31.3)

    report = {
        "aoi_id": "aoi-levant",
        "datetime": date_key,
        "composite_score": 0.62,
        "is_anomaly": True,
        "signals": [
            {
                "signal": "vegetation_change",
                "weight": 0.35,
                "value": 0.4,
                "threshold": 0.15,
                "triggered": True,
                "description": "veg",
            }
        ],
    }
    anom_dir = data / "processed" / "anomalies" / "aoi-levant"
    anom_dir.mkdir(parents=True)
    (anom_dir / f"report_{date_key}.json").write_text(json.dumps(report), encoding="utf-8")
    score_path = anom_dir / f"anomaly_score_{date_key}.tif"
    write_geotiff(score_path, bounds, width=32, height=32, seed=7, value_scale=1.0)

    correlation = {
        "aoi_id": "aoi-levant",
        "fusion_confidence": 0.58,
        "sources_agreeing": ["gdelt"],
        "keywords_used": ["fire"],
        "matches": [
            {
                "event_id": "ev-1",
                "source": "gdelt",
                "confidence": 0.6,
                "title": "Wildfire near coast",
                "datetime": now.isoformat(),
                "explanation": "keyword overlap",
            }
        ],
    }
    corr_dir = data / "processed" / "osint" / "correlations" / "aoi-levant"
    corr_dir.mkdir(parents=True)
    (corr_dir / f"correlation_{run_id}.json").write_text(json.dumps(correlation), encoding="utf-8")

    # NDVI pair for before/after
    feat_root = data / "processed" / "features" / "aoi-levant"
    for d in ("20250101", "20250108"):
        ddir = feat_root / d
        ddir.mkdir(parents=True)
        write_geotiff(ddir / "ndvi.tif", bounds, width=32, height=32, seed=int(d), value_scale=0.5)

    monkeypatch.setenv("DATA_ROOT", str(data))
    monkeypatch.setenv("REGISTRY_PATH", str(registry))
    _clear_caches()
    yield data, run_id
    _clear_caches()


def test_colormap_and_heatmap_png(tmp_path: Path):
    import numpy as np

    arr = np.linspace(0, 1, 16).reshape(4, 4).astype(np.float32)
    rgb = apply_colormap(arr)
    assert rgb.shape == (4, 4, 3)
    out = tmp_path / "hm.png"
    raster_to_heatmap_png(arr, out, max_width=64)
    assert out.exists()


def test_confidence_and_timeline():
    anomaly = {"composite_score": 0.7, "is_anomaly": True, "datetime": "20250101", "signals": []}
    corr = {"fusion_confidence": 0.5, "matches": [{"datetime": "2025-01-01", "title": "x", "confidence": 0.4, "source": "gdelt"}]}
    breakdown = build_confidence_breakdown("aoi-levant", anomaly, corr)
    assert breakdown["geospatial"]["composite_score"] == 0.7
    assert breakdown["osint"]["fusion_confidence"] == 0.5
    events = build_timeline("aoi-levant", anomaly, corr)
    assert len(events) >= 2


def test_run_explainability(explainability_env):
    data, run_id = explainability_env
    result = run_explainability(run_id=run_id)
    assert result.artifacts_total >= 1
    manifest = data / "explainability" / "aoi-levant" / run_id / "manifest.json"
    assert manifest.exists()
    bundle = json.loads(manifest.read_text(encoding="utf-8"))
    assert bundle["aoi_id"] == "aoi-levant"
    types = {a["type"] for a in bundle["artifacts"]}
    assert "confidence" in types
    assert "timeline" in types


def test_generate_alerts(explainability_env):
    _, run_id = explainability_env
    result = generate_alerts(run_id=run_id)
    assert len(result.alerts) >= 1
    assert result.alerts[0].severity.value in ("medium", "high", "critical")
