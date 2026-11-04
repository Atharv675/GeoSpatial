"""
Raster-to-PNG heatmap rendering (operational explainability).

Uses Pillow + numpy — no ML explainability frameworks.
"""

from pathlib import Path

import numpy as np
from PIL import Image

# Diverging colormap: low=blue, mid=white, high=red (anomaly emphasis)
_COLORMAP = np.array(
    [
        [49, 54, 149],
        [116, 173, 209],
        [224, 243, 248],
        [254, 224, 144],
        [253, 174, 97],
        [215, 48, 39],
        [165, 0, 38],
    ],
    dtype=np.uint8,
)


def _normalize_to_unit(data: np.ndarray) -> np.ndarray:
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


def apply_colormap(values: np.ndarray) -> np.ndarray:
    """Map normalized 0-1 array to RGB uint8."""
    idx = (values * (_COLORMAP.shape[0] - 1)).astype(np.int32)
    idx = np.clip(idx, 0, _COLORMAP.shape[0] - 1)
    return _COLORMAP[idx]


def raster_to_heatmap_png(
    data: np.ndarray,
    output_path: Path,
    *,
    max_width: int = 512,
) -> Path:
    """Write a downsampled heatmap PNG from 2D float array."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    norm = _normalize_to_unit(data.astype(np.float32))
    rgb = apply_colormap(norm)
    mask = ~np.isfinite(data)
    rgb[mask] = [40, 40, 40]

    img = Image.fromarray(rgb, mode="RGB")
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.Resampling.BILINEAR)
    img.save(output_path, format="PNG", optimize=True)
    return output_path
