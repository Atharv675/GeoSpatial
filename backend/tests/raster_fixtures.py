"""Helpers to create minimal GeoTIFF fixtures for preprocessing tests."""

from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.transform import from_bounds


def aoi_bounds(geometry: dict[str, Any]) -> tuple[float, float, float, float]:
    """Return west, south, east, north from Polygon geometry."""
    coords = geometry["coordinates"][0]
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return min(lons), min(lats), max(lons), max(lats)


def write_geotiff(
    path: Path,
    bounds: tuple[float, float, float, float],
    *,
    width: int = 128,
    height: int = 128,
    seed: int = 0,
    value_scale: float = 1000.0,
) -> None:
    """Write a single-band float32 GeoTIFF in EPSG:4326."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    data = (rng.random((height, width), dtype=np.float32) * value_scale).astype(np.float32)
    transform = from_bounds(*bounds, width, height)
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "count": 1,
        "width": width,
        "height": height,
        "crs": "EPSG:4326",
        "transform": transform,
        "compress": "deflate",
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data, 1)
