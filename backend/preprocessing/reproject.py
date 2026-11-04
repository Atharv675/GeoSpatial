"""
Reprojection to project target CRS (EPSG:3857 default).

Uses Rasterio warp — GDAL-backed, limited to reprojection only.
"""

from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import Resampling, calculate_default_transform, reproject

from backend.shared.config import get_settings
from backend.shared.logging import get_logger

logger = get_logger(__name__)


def reproject_raster(src_path: Path, dst_path: Path, dst_epsg: int | None = None) -> Path:
    """Reproject single-band raster to target CRS."""
    settings = get_settings()
    epsg = dst_epsg or settings.target_crs_epsg
    dst_crs = rasterio.crs.CRS.from_epsg(epsg)

    dst_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(src_path) as src:
        transform, width, height = calculate_default_transform(
            src.crs,
            dst_crs,
            src.width,
            src.height,
            *src.bounds,
        )
        profile = src.profile.copy()
        profile.update(
            crs=dst_crs,
            transform=transform,
            width=width,
            height=height,
            dtype="float32",
            compress="deflate",
        )
        block = min(settings.raster_chunk_size, width, height)
        block = (block // 16) * 16
        if block >= 16:
            profile.update(tiled=True, blockxsize=block, blockysize=block)

        with rasterio.open(dst_path, "w", **profile) as dst:
            for band_idx in range(1, src.count + 1):
                data = np.zeros((height, width), dtype=np.float32)
                reproject(
                    source=rasterio.band(src, band_idx),
                    destination=data,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.bilinear,
                )
                dst.write(data, band_idx)

    logger.info("raster_reprojected", src=str(src_path), dst=str(dst_path), epsg=epsg)
    return dst_path
