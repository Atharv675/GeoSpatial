"""
Clip rasters to AOI polygon using Rasterio mask.
"""

from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.mask import mask as rio_mask
from rasterio.warp import transform_geom

from backend.shared.logging import get_logger

AOI_CRS = "EPSG:4326"

logger = get_logger(__name__)


def clip_raster_to_geometry(
    src_path: Path,
    dst_path: Path,
    geometry: dict[str, Any],
    *,
    crop: bool = True,
) -> Path:
    """Clip raster to a GeoJSON Polygon geometry."""
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(src_path) as src:
        geom = geometry
        if src.crs and str(src.crs) != AOI_CRS:
            geom = transform_geom(AOI_CRS, src.crs, geometry)
        out_image, out_transform = rio_mask(src, [geom], crop=crop, filled=True, nodata=np.nan)
        profile = src.profile.copy()
        profile.update(
            height=out_image.shape[1],
            width=out_image.shape[2],
            transform=out_transform,
            dtype="float32",
            nodata=np.nan,
            compress="deflate",
        )
        with rasterio.open(dst_path, "w", **profile) as dst:
            dst.write(out_image.astype(np.float32))

    logger.info("raster_clipped", src=str(src_path), dst=str(dst_path))
    return dst_path
