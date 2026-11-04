"""Phase 8 end-to-end HTTP contract tests."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.shared.config import get_settings
from backend.tests.raster_fixtures import write_geotiff


def _clear_caches() -> None:
    get_settings.cache_clear()


@pytest.fixture
def e2e_data_env(tmp_path: Path, monkeypatch):
    """Minimal processed + explainability state for dashboard API contract."""
    data = tmp_path / "data"
    registry = data / "registry"
    registry.mkdir(parents=True)
    aois_src = Path(__file__).resolve().parents[2] / "data" / "registry" / "aois.json"
    (registry / "aois.json").write_text(aois_src.read_text(encoding="utf-8"), encoding="utf-8")
    catalog_src = Path(__file__).resolve().parents[2] / "data" / "registry" / "catalog.json"
    if catalog_src.exists():
        (registry / "catalog.json").write_text(
            catalog_src.read_text(encoding="utf-8"), encoding="utf-8"
        )

    now = datetime.now(timezone.utc)
    date_key = now.strftime("%Y%m%d")
    run_id = "e2e-test-run"
    bounds = (34.75, 31.2, 34.85, 31.3)

    report = {
        "aoi_id": "aoi-levant",
        "datetime": date_key,
        "composite_score": 0.62,
        "is_anomaly": True,
        "signals": [{"signal": "vegetation_change", "triggered": True, "value": 0.4}],
    }
    anom_dir = data / "processed" / "anomalies" / "aoi-levant"
    anom_dir.mkdir(parents=True)
    (anom_dir / f"report_{date_key}.json").write_text(json.dumps(report), encoding="utf-8")
    write_geotiff(anom_dir / f"anomaly_score_{date_key}.tif", bounds, width=32, height=32, seed=1)

    correlation = {
        "aoi_id": "aoi-levant",
        "fusion_confidence": 0.55,
        "matches": [
            {
                "event_id": "ev-1",
                "source": "gdelt",
                "confidence": 0.6,
                "title": "Demo event",
                "datetime": now.isoformat(),
            }
        ],
        "sources_agreeing": ["gdelt"],
        "keywords_used": ["fire"],
    }
    corr_dir = data / "processed" / "osint" / "correlations" / "aoi-levant"
    corr_dir.mkdir(parents=True)
    (corr_dir / f"correlation_{run_id}.json").write_text(json.dumps(correlation), encoding="utf-8")

    exp_dir = data / "explainability" / "aoi-levant" / run_id
    (exp_dir / "overlays").mkdir(parents=True)
    (exp_dir / "heatmaps").mkdir(parents=True)

    aoi_geo = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"aoi_id": "aoi-levant", "name": "Levant"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [34.75, 31.2],
                            [34.85, 31.2],
                            [34.85, 31.3],
                            [34.75, 31.3],
                            [34.75, 31.2],
                        ]
                    ],
                },
            }
        ],
    }
    (exp_dir / "overlays" / "aoi_boundary.geojson").write_text(
        json.dumps(aoi_geo), encoding="utf-8"
    )

    manifest = {
        "aoi_id": "aoi-levant",
        "run_id": run_id,
        "artifacts": [
            {
                "type": "overlay",
                "aoi_id": "aoi-levant",
                "name": "aoi_boundary",
                "path": f"explainability/aoi-levant/{run_id}/overlays/aoi_boundary.geojson",
                "description": "boundary",
            }
        ],
        "timeline": [
            {
                "datetime": date_key,
                "label": "Assessment",
                "category": "anomaly",
                "score": 0.62,
                "source": "geospatial",
            }
        ],
        "confidence_breakdown": {
            "aoi_id": "aoi-levant",
            "geospatial": {"composite_score": 0.62, "is_anomaly": True},
            "osint": {"fusion_confidence": 0.55},
            "fusion": {"combined_assessment": "test"},
        },
    }
    (exp_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    state = {
        "last_run": {
            "run_id": run_id,
            "artifacts_total": 1,
            "bundles": [{"aoi_id": "aoi-levant"}],
        }
    }
    (data / "explainability" / "explainability_state.json").write_text(
        json.dumps(state), encoding="utf-8"
    )

    monkeypatch.setenv("DATA_ROOT", str(data))
    monkeypatch.setenv("REGISTRY_PATH", str(registry))
    _clear_caches()
    yield
    _clear_caches()


def test_e2e_api_contract(e2e_data_env):
    """Validate Phase 7/8 analyst API surface."""
    client = TestClient(create_app())

    assert client.get("/api/v1/health").json()["status"] == "ok"
    ready = client.get("/api/v1/ready").json()
    assert ready["status"] in ("ready", "degraded")

    aois = client.get("/api/v1/aois")
    assert aois.status_code == 200
    assert aois.json()["count"] >= 1

    status = client.get("/api/v1/explainability/status")
    assert status.status_code == 200
    assert status.json()["has_run"] is True

    manifest = client.get("/api/v1/explainability/aoi-levant/manifest")
    assert manifest.status_code == 200
    body = manifest.json()
    assert body["run_id"] == "e2e-test-run"
    assert len(body["artifacts"]) >= 1

    artifact_path = body["artifacts"][0]["path"]
    art = client.get(
        f"/api/v1/explainability/aoi-levant/artifact?path={artifact_path}"
    )
    assert art.status_code == 200

    alerts = client.get("/api/v1/alerts/status")
    assert alerts.status_code == 200


@pytest.mark.integration
def test_e2e_bootstrap_script(tmp_path: Path, monkeypatch):
    """Full seed + pipeline bootstrap (slow; requires rasterio)."""
    pytest.importorskip("rasterio")
    import os
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[2]
    data = tmp_path / "data"
    registry = data / "registry"
    registry.mkdir(parents=True)
    aois_src = root / "data" / "registry" / "aois.json"
    (registry / "aois.json").write_text(aois_src.read_text(encoding="utf-8"), encoding="utf-8")

    env = os.environ.copy()
    env["DATA_ROOT"] = str(data)
    env["REGISTRY_PATH"] = str(registry)
    env["PYTHONPATH"] = str(root)

    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "e2e_bootstrap.py"), "--force"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout, result.stderr)
    assert result.returncode == 0
    assert (data / "explainability" / "aoi-levant").exists()
