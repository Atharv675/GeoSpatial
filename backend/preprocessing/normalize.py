"""
Per-raster normalization (deterministic min-max to 0–1).

Uses numpy on float32 arrays — memory-safe via Rasterio single-band read.
"""

from pathlib import Path

import numpy as np
import rasterio

from backend.shared.logging import get_logger

logger = get_logger(__name__)


def normalize_band(data: np.ndarray) -> np.ndarray:
    """Min-max normalize valid pixels to [0, 1]."""
    valid = np.isfinite(data)
    if not valid.any():
        return np.zeros_like(data, dtype=np.float32)
    vmin = float(np.nanmin(data[valid]))
    vmax = float(np.nanmax(data[valid]))
    if vmax <= vmin:
        out = np.zeros_like(data, dtype=np.float32)
        out[valid] = 0.5
        return out
    out = (data - vmin) / (vmax - vmin)
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def normalize_raster(src_path: Path, dst_path: Path) -> Path:
    """Normalize raster band in-place to new file."""
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(src_path) as src:
        data = src.read(1).astype(np.float32)
        normalized = normalize_band(data)
        profile = src.profile.copy()
        profile.update(dtype="float32", nodata=np.nan, compress="deflate")
        with rasterio.open(dst_path, "w", **profile) as dst:
            dst.write(normalized, 1)

    logger.info("raster_normalized", src=str(src_path), dst=str(dst_path))
    return dst_path
