#!/usr/bin/env python3
"""
Seed curated GeoTIFF rasters and write checksums into curated_manifest.json.

Requires raster dependencies (pip install -r requirements/raster.txt).
"""

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data"
REGISTRY = DATA_ROOT / "registry"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1024 * 256):
            digest.update(chunk)
    return digest.hexdigest()


def load_aoi_bounds() -> dict[str, tuple[float, float, float, float]]:
    aois_path = REGISTRY / "aois.json"
    with aois_path.open(encoding="utf-8") as f:
        data = json.load(f)
    bounds: dict[str, tuple[float, float, float, float]] = {}
    for aoi in data["aois"]:
        coords = aoi["geometry"]["coordinates"][0]
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        bounds[aoi["aoi_id"]] = (min(lons), min(lats), max(lons), max(lats))
    return bounds


def write_geotiff(path: Path, bounds: tuple[float, float, float, float], seed: int) -> None:
    import numpy as np
    import rasterio
    from rasterio.transform import from_bounds

    width, height = 512, 512
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    data = (rng.random((height, width), dtype=np.float32) * 2000.0 + 100.0).astype(np.float32)
    transform = from_bounds(*bounds, width, height)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
        compress="deflate",
        tiled=True,
        blockxsize=256,
        blockysize=256,
    ) as dst:
        dst.write(data, 1)


def build_asset_specs(now: datetime, aoi_bounds_map: dict) -> list[dict]:
    d = lambda days: now - timedelta(days=days)
    specs = [
        ("s2-levant-w1-b04", "sentinel-2", "sentinel-2-l2a", "aoi-levant", d(21), "B04_w1.tif", ["B04"], 101, 5),
        ("s2-levant-w1-b08", "sentinel-2", "sentinel-2-l2a", "aoi-levant", d(21), "B08_w1.tif", ["B08"], 111, 5),
        ("s2-levant-w2-b04", "sentinel-2", "sentinel-2-l2a", "aoi-levant", d(14), "B04_w2.tif", ["B04"], 102, 8),
        ("s2-levant-w2-b08", "sentinel-2", "sentinel-2-l2a", "aoi-levant", d(14), "B08_w2.tif", ["B08"], 112, 8),
        ("s2-delta-w1-b04", "sentinel-2", "sentinel-2-l2a", "aoi-delta", d(18), "B04_w1.tif", ["B04"], 103, 3),
        ("s2-delta-w1-b08", "sentinel-2", "sentinel-2-l2a", "aoi-delta", d(18), "B08_w1.tif", ["B08"], 113, 3),
        ("s1-levant-w1-vv", "sentinel-1", "sentinel-1-grd", "aoi-levant", d(20), "VV_w1.tif", ["VV"], 201, None),
        ("s1-levant-w2-vv", "sentinel-1", "sentinel-1-grd", "aoi-levant", d(13), "VV_w2.tif", ["VV"], 202, None),
        ("s1-delta-w1-vv", "sentinel-1", "sentinel-1-grd", "aoi-delta", d(17), "VV_w1.tif", ["VV"], 203, None),
    ]
    assets = []
    for (
        asset_id,
        platform,
        collection,
        aoi_id,
        dt,
        filename,
        bands,
        seed,
        cloud,
    ) in specs:
        rel = f"raw/curated/{collection}/{aoi_id}/{filename}"
        path = DATA_ROOT / Path(rel)
        write_geotiff(path, aoi_bounds_map[aoi_id], seed)
        meta = {
            "id": asset_id,
            "platform": platform,
            "collection": collection,
            "aoi_id": aoi_id,
            "datetime": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "filename": filename,
            "bands": bands,
            "source": {"type": "local", "path": rel},
            "checksum_sha256": sha256_file(path),
            "properties": {},
        }
        if cloud is not None:
            meta["properties"]["eo:cloud_cover"] = cloud
        if platform == "sentinel-1":
            meta["polarization"] = "VV"
            meta["properties"]["sar:instrument_mode"] = "IW"
        assets.append(meta)
        print(f"  wrote {rel}")
    return assets


def main() -> int:
    try:
        import rasterio  # noqa: F401
    except ImportError:
        print("ERROR: rasterio required. Run: pip install -r requirements/raster.txt", file=sys.stderr)
        return 1

    now = datetime.now(timezone.utc)
    print("Seeding curated GeoTIFF assets (512x512)…")
    bounds_map = load_aoi_bounds()
    assets = build_asset_specs(now, bounds_map)
    manifest = {
        "version": "1",
        "description": "Curated Sentinel GeoTIFF assets for GeoSentinel",
        "assets": assets,
    }
    manifest_path = REGISTRY / "curated_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote manifest: {manifest_path} ({len(assets)} assets)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
