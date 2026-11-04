"""
Temporal differencing between consecutive feature rasters.

Used for vegetation, water, burn, and optical change detection.
"""

from pathlib import Path

import numpy as np

from backend.processing.io import read_band, write_feature_raster
from backend.shared.logging import get_logger

logger = get_logger(__name__)


def temporal_difference(
    previous_path: Path,
    current_path: Path,
    output_path: Path,
) -> Path:
    """
    Compute current - previous (deterministic temporal diff).

    Both rasters must share shape and georeferencing.
    """
    prev, profile = read_band(previous_path)
    curr, _ = read_band(current_path)
    if prev.shape != curr.shape:
        raise ValueError("Temporal pair shape mismatch")

    diff = np.where(np.isfinite(prev) & np.isfinite(curr), curr - prev, np.nan)
    write_feature_raster(output_path, diff.astype(np.float32), profile)
    logger.info(
        "temporal_diff_computed",
        previous=str(previous_path),
        current=str(current_path),
        mean_delta=float(np.nanmean(diff)),
    )
    return output_path
