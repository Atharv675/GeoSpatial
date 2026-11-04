"""
Spectral indices: NDVI, NDWI, NBR.

Modular, deterministic calculations on normalized reflectance rasters.
Curated single-band assets are paired by AOI and acquisition time in analyze.py.
"""

import numpy as np

from backend.shared.logging import get_logger

logger = get_logger(__name__)

# Sentinel-2 band name mapping
BAND_RED = {"B04", "red"}
BAND_NIR = {"B08", "B8A", "nir"}
BAND_GREEN = {"B03", "green"}
BAND_SWIR = {"B11", "B12", "swir"}


def _safe_index(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    """Compute (num - den) / (num + den) with NaN for invalid pixels."""
    out = np.full_like(numerator, np.nan, dtype=np.float32)
    valid = np.isfinite(numerator) & np.isfinite(denominator)
    denom = numerator[valid] + denominator[valid]
    mask = denom != 0
    idx_valid = np.where(valid)
    out[idx_valid[0][mask], idx_valid[1][mask]] = (
        (numerator[valid][mask] - denominator[valid][mask]) / denom[mask]
    )
    return out


def compute_ndvi(red: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """NDVI = (NIR - RED) / (NIR + RED). Vegetation vigor."""
    result = _safe_index(nir, red)
    logger.info("ndvi_computed", finite_pixels=int(np.isfinite(result).sum()))
    return result


def compute_ndwi(green: np.ndarray, nir: np.ndarray) -> np.ndarray:
    """NDWI = (GREEN - NIR) / (GREEN + NIR). Water/moisture."""
    result = _safe_index(green, nir)
    logger.info("ndwi_computed", finite_pixels=int(np.isfinite(result).sum()))
    return result


def compute_nbr(nir: np.ndarray, swir: np.ndarray) -> np.ndarray:
    """NBR = (NIR - SWIR) / (NIR + SWIR). Burn severity proxy."""
    result = _safe_index(nir, swir)
    logger.info("nbr_computed", finite_pixels=int(np.isfinite(result).sum()))
    return result


def classify_band(band_name: str) -> str | None:
    """Map STAC/curated band id to spectral role."""
    upper = band_name.upper()
    if upper in BAND_RED:
        return "red"
    if upper in BAND_NIR:
        return "nir"
    if upper in BAND_GREEN:
        return "green"
    if upper in BAND_SWIR:
        return "swir"
    return None
