"""
Raster validation before processing.

Validates CRS, dimensions, dtype, and file size — does not trust metadata blindly.
"""

from pathlib import Path

import rasterio

from backend.shared.config import get_settings
from backend.shared.exceptions import ValidationError
from backend.shared.logging import get_logger

logger = get_logger(__name__)

ALLOWED_DTYPES = {"uint8", "uint16", "int16", "float32", "float64"}


def validate_raster(path: Path) -> dict[str, object]:
    """
    Validate a GeoTIFF and return safe metadata summary.

    Raises ValidationError on failure.
    """
    if not path.exists() or not path.is_file():
        raise ValidationError(f"Raster not found: {path.name}")

    settings = get_settings()
    if path.stat().st_size == 0:
        raise ValidationError(f"Raster is empty: {path.name}")

    try:
        with rasterio.open(path) as src:
            if src.count < 1:
                raise ValidationError("Raster has no bands")
            if src.width < 1 or src.height < 1:
                raise ValidationError("Invalid raster dimensions")
            pixels = src.width * src.height
            if pixels > settings.max_raster_pixels:
                raise ValidationError(
                    f"Raster exceeds max pixel budget ({pixels} > {settings.max_raster_pixels})"
                )
            if src.crs is None:
                raise ValidationError("Raster CRS is missing")
            dtype_name = src.dtypes[0]
            if dtype_name not in ALLOWED_DTYPES:
                raise ValidationError(f"Unsupported dtype: {dtype_name}")

            summary = {
                "width": src.width,
                "height": src.height,
                "count": src.count,
                "dtype": dtype_name,
                "crs": str(src.crs),
                "bounds": list(src.bounds),
            }
    except rasterio.errors.RasterioIOError as exc:
        raise ValidationError(f"Invalid raster file: {path.name}") from exc

    logger.info("raster_validated", path=str(path), width=summary["width"], height=summary["height"])
    return summary
