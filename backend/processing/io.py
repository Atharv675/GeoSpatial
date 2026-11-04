"""
Raster I/O helpers for feature engineering outputs.
"""

from pathlib import Path

import numpy as np
import rasterio

from backend.shared.logging import get_logger

logger = get_logger(__name__)


def read_band(path: Path) -> tuple[np.ndarray, dict]:
    """Read single band and profile from GeoTIFF."""
    with rasterio.open(path) as src:
        data = src.read(1).astype(np.float32)
        profile = src.profile.copy()
    return data, profile


def write_feature_raster(path: Path, data: np.ndarray, profile: dict) -> Path:
    """Write float32 feature raster with compression."""
    path.parent.mkdir(parents=True, exist_ok=True)
    out_profile = profile.copy()
    out_profile.update(dtype="float32", count=1, nodata=np.nan, compress="deflate")
    with rasterio.open(path, "w", **out_profile) as dst:
        dst.write(data.astype(np.float32), 1)
    logger.info("feature_raster_written", path=str(path))
    return path


def raster_mean_valid(data: np.ndarray) -> float:
    """Mean of finite pixels."""
    valid = np.isfinite(data)
    if not valid.any():
        return 0.0
    return float(np.mean(data[valid]))
