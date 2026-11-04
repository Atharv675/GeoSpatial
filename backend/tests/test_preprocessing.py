"""Phase 3 raster preprocessing tests."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest
import rasterio

from backend.ingestion.aoi import get_active_aois
from backend.preprocessing.normalize import normalize_band
from backend.preprocessing.preprocess import preprocess_registry_item, run_preprocessing
from backend.preprocessing.sar_diff import compute_sar_disturbance
from backend.preprocessing.tile import generate_tiles
from backend.preprocessing.validate import validate_raster
from backend.shared.config import get_settings
from backend.storage.registry import MetadataRegistry
from backend.tests.raster_fixtures import aoi_bounds, write_geotiff


def _clear_caches() -> None:
    get_settings.cache_clear()
    get_active_aois.cache_clear()


@pytest.fixture
def preprocess_env(tmp_path: Path, monkeypatch):
    data = tmp_path / "data"
    registry = data / "registry"
    registry.mkdir(parents=True)
    (data / "raw").mkdir(parents=True)
    (data / "processed").mkdir(parents=True)

    aois_src = Path(__file__).resolve().parents[2] / "data" / "registry" / "aois.json"
    (registry / "aois.json").write_text(aois_src.read_text(encoding="utf-8"), encoding="utf-8")
    aois = json.loads(aois_src.read_text(encoding="utf-8"))

    bounds = aoi_bounds(aois["aois"][0]["geometry"])
    raw_path = data / "raw" / "sentinel-2-l2a" / "aoi-levant" / "20260501" / "test.tif"
    write_geotiff(raw_path, bounds, width=256, height=256, seed=42)

    item = {
        "type": "Item",
        "id": "test-s2-item",
        "collection": "sentinel-2-l2a",
        "properties": {
            "datetime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "platform": "sentinel-2",
            "gs:collection": "sentinel-2-l2a",
            "gs:aoi_id": "aoi-levant",
            "eo:cloud_cover": 5,
        },
        "assets": {
            "data": {
                "href": str(raw_path.relative_to(data)).replace("\\", "/"),
                "type": "image/tiff",
            }
        },
        "geometry": aois["aois"][0]["geometry"],
    }
    catalog = {"type": "Catalog", "id": "t", "stac_version": "1.0.0", "items": [item]}
    (registry / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")

    monkeypatch.setenv("DATA_ROOT", str(data))
    monkeypatch.setenv("REGISTRY_PATH", str(registry))
    monkeypatch.setenv("TILE_SIZE", "256")
    monkeypatch.setenv("RASTER_CHUNK_SIZE", "128")
    _clear_caches()
    yield data, registry, item
    _clear_caches()


def test_validate_raster_rejects_invalid(tmp_path: Path):
    bad = tmp_path / "bad.tif"
    bad.write_bytes(b"not a geotiff")
    with pytest.raises(Exception):
        validate_raster(bad)


def test_normalize_band():
    arr = np.array([[0.0, 50.0], [100.0, np.nan]], dtype=np.float32)
    out = normalize_band(arr)
    assert float(np.nanmax(out[np.isfinite(out)])) == pytest.approx(1.0)
    assert float(np.nanmin(out[np.isfinite(out)])) == pytest.approx(0.0)


def test_generate_tiles(preprocess_env):
    data, _, _ = preprocess_env
    norm = data / "processed" / "test_norm.tif"
    write_geotiff(norm, (34.75, 31.2, 34.85, 31.3), width=100, height=100, seed=1)
    tiles = generate_tiles(norm, data / "tiles", tile_size=256)
    assert len(tiles) >= 1


def test_sar_disturbance(tmp_path: Path):
    bounds = (34.75, 31.2, 34.85, 31.3)
    prev = tmp_path / "prev.tif"
    curr = tmp_path / "curr.tif"
    out = tmp_path / "diff.tif"
    write_geotiff(prev, bounds, width=64, height=64, seed=1, value_scale=500)
    write_geotiff(curr, bounds, width=64, height=64, seed=2, value_scale=800)
    compute_sar_disturbance(prev, curr, out)
    with rasterio.open(out) as ds:
        diff = ds.read(1)
    assert np.nanmax(np.abs(diff)) > 0


def test_preprocess_registry_item(preprocess_env):
    _, _, item = preprocess_env
    result = preprocess_registry_item(item)
    assert result.status.value in ("ok", "skipped")
    assert "normalized" in result.outputs
    settings = get_settings()
    norm_path = settings.resolve_data_path(result.outputs["normalized"])
    assert norm_path.exists()


def test_run_preprocessing_sar_and_stack(preprocess_env):
    data, registry, _ = preprocess_env
    now = datetime.now(timezone.utc)

    items = []
    for i, (coll, platform) in enumerate(
        [("sentinel-2-l2a", "sentinel-2"), ("sentinel-1-grd", "sentinel-1")]
    ):
        for j in range(2):
            iid = f"multi-{coll}-{j}"
            rel = f"raw/{coll}/aoi-levant/{iid}.tif"
            path = data / rel
            write_geotiff(path, (34.75, 31.2, 34.85, 31.3), width=256, height=256, seed=10 + i + j)
            props = {
                "datetime": (now - timedelta(days=10 - j)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "platform": platform,
                "gs:collection": coll,
                "gs:aoi_id": "aoi-levant",
            }
            if platform == "sentinel-2":
                props["eo:cloud_cover"] = 5
            items.append(
                {
                    "type": "Item",
                    "id": iid,
                    "collection": coll,
                    "properties": props,
                    "assets": {"data": {"href": rel.replace("\\", "/")}},
                    "geometry": json.loads((registry / "aois.json").read_text())["aois"][0]["geometry"],
                }
            )

    catalog = {"type": "Catalog", "id": "t", "stac_version": "1.0.0", "items": items}
    (registry / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
    _clear_caches()

    result = run_preprocessing(run_id="test-pre")
    assert result.items_ok >= 2
    s1_diffs = [d for d in result.sar_diffs if d.status.value == "ok"]
    assert len(s1_diffs) >= 1
    stacks_ok = [s for s in result.stacks if s.status.value == "ok"]
    assert len(stacks_ok) >= 1


@pytest.mark.anyio
async def test_api_preprocessing_run(client, preprocess_env):
    _clear_caches()
    result_item = preprocess_registry_item(preprocess_env[2])
    assert result_item.status.value in ("ok", "skipped")

    r = await client.post("/api/v1/preprocessing/run", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["items_total"] >= 1
