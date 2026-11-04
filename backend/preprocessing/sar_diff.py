"""
Sentinel-1 temporal SAR differencing.

Current SAR - Previous SAR = Disturbance score (simplified Phase 3 scope).
"""

from pathlib import Path

import numpy as np
import rasterio

from backend.shared.logging import get_logger

logger = get_logger(__name__)


def compute_sar_disturbance(
    previous_path: Path,
    current_path: Path,
    output_path: Path,
) -> Path:
    """
    Compute temporal SAR difference (current - previous).

    Both rasters must be same shape/CRS after preprocessing.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(previous_path) as prev, rasterio.open(current_path) as curr:
        if prev.shape != curr.shape:
            raise ValueError("SAR pair shape mismatch for differencing")
        prev_data = prev.read(1).astype(np.float32)
        curr_data = curr.read(1).astype(np.float32)
        disturbance = curr_data - prev_data
        disturbance = np.where(
            np.isfinite(prev_data) & np.isfinite(curr_data),
            disturbance,
            np.nan,
        )
        profile = curr.profile.copy()
        profile.update(dtype="float32", nodata=np.nan, compress="deflate")
        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(disturbance.astype(np.float32), 1)

    logger.info(
        "sar_disturbance_computed",
        previous=str(previous_path),
        current=str(current_path),
        output=str(output_path),
    )
    return output_path
