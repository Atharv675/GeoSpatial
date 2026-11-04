"""
Cloud masking for Sentinel-2 curated assets.

Curated pipeline uses eo:cloud_cover metadata when SCL band is unavailable.
"""

from pathlib import Path

import numpy as np
import rasterio

from backend.shared.config import get_settings
from backend.shared.logging import get_logger

logger = get_logger(__name__)


def build_cloud_mask_array(
    shape: tuple[int, int],
    cloud_cover_pct: float,
) -> np.ndarray:
    """
    Build binary cloud mask (1=clear, 0=cloud).

    When cloud cover exceeds threshold, mask all pixels as cloudy.
    """
    settings = get_settings()
    clear = np.zeros(shape, dtype=np.uint8)
    if cloud_cover_pct <= settings.cloud_cover_threshold:
        clear[:] = 1
    return clear


def apply_cloud_mask_raster(
    src_path: Path,
    dst_path: Path,
    cloud_cover_pct: float,
    mask_path: Path | None = None,
) -> Path:
    """Apply cloud mask to raster (NaN where cloudy)."""
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(src_path) as src:
        data = src.read(1).astype(np.float32)
        cloud_mask = build_cloud_mask_array((src.height, src.width), cloud_cover_pct)
        if cloud_mask.sum() == 0:
            data[:] = np.nan
        profile = src.profile.copy()
        profile.update(dtype="float32", nodata=np.nan, compress="deflate")

        with rasterio.open(dst_path, "w", **profile) as dst:
            dst.write(data, 1)

        if mask_path:
            mask_path.parent.mkdir(parents=True, exist_ok=True)
            mask_profile = profile.copy()
            mask_profile.update(dtype="uint8", nodata=0)
            with rasterio.open(mask_path, "w", **mask_profile) as mdst:
                mdst.write(cloud_mask, 1)

    logger.info(
        "cloud_mask_applied",
        src=str(src_path),
        cloud_cover=cloud_cover_pct,
        clear_pixels=int(cloud_mask.sum()),
    )
    return dst_path
