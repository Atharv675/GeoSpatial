"""
Before/after comparison imagery for analyst explainability.

Renders side-by-side PNG pairs from consecutive normalized or feature rasters.
"""

from pathlib import Path

import numpy as np
import rasterio
from PIL import Image

from backend.explainability.colormap import apply_colormap
from backend.explainability.models import ArtifactType, ExplainabilityArtifact
from backend.shared.config import get_settings
from backend.shared.logging import get_logger

logger = get_logger(__name__)


def _rel(path: Path) -> str:
    return str(path.relative_to(get_settings().data_root)).replace("\\", "/")


def _raster_to_rgb_array(path: Path, max_width: int) -> np.ndarray | None:
    if not path.exists():
        return None
    with rasterio.open(path) as src:
        data = src.read(1).astype(np.float32)
    valid = np.isfinite(data)
    if not valid.any():
        return None
    vmin, vmax = float(np.nanmin(data[valid])), float(np.nanmax(data[valid]))
    norm = np.clip((data - vmin) / max(vmax - vmin, 1e-6), 0, 1)
    rgb = apply_colormap(norm)
    rgb[~valid] = [40, 40, 40]
    img = Image.fromarray(rgb, mode="RGB")
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.Resampling.BILINEAR)
    return np.array(img)


def create_before_after_png(
    before_path: Path,
    after_path: Path,
    output_path: Path,
    aoi_id: str,
    label: str,
) -> ExplainabilityArtifact | None:
    """Combine two rasters into one side-by-side PNG."""
    settings = get_settings()
    w = settings.explainability_png_width // 2
    before_rgb = _raster_to_rgb_array(before_path, w)
    after_rgb = _raster_to_rgb_array(after_path, w)
    if before_rgb is None or after_rgb is None:
        return None

    h = max(before_rgb.shape[0], after_rgb.shape[0])
    combined = Image.new("RGB", (before_rgb.shape[1] + after_rgb.shape[1], h), (30, 30, 30))
    combined.paste(Image.fromarray(before_rgb), (0, 0))
    combined.paste(Image.fromarray(after_rgb), (before_rgb.shape[1], 0))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.save(output_path, format="PNG", optimize=True)

    logger.info("before_after_created", label=label, aoi_id=aoi_id)
    return ExplainabilityArtifact(
        type=ArtifactType.BEFORE_AFTER,
        aoi_id=aoi_id,
        name=label,
        path=_rel(output_path),
        description="Before (left) vs after (right) comparison",
        metadata={"before": _rel(before_path), "after": _rel(after_path)},
    )


def generate_before_after_pairs(aoi_id: str, run_id: str) -> list[ExplainabilityArtifact]:
    """Find consecutive feature or normalized pairs and render comparisons."""
    settings = get_settings()
    out_dir = settings.resolve_data_path(f"explainability/{aoi_id}/{run_id}/before_after")
    artifacts: list[ExplainabilityArtifact] = []

    # NDVI temporal: parse diff filename for dates, load underlying feature dates
    feat_root = settings.resolve_data_path(f"processed/features/{aoi_id}")
    date_dirs: list[Path] = []
    if feat_root.exists():
        date_dirs = sorted(
            [d for d in feat_root.iterdir() if d.is_dir() and d.name.isdigit()],
            key=lambda p: p.name,
        )
    if len(date_dirs) >= 2:
        prev_ndvi = date_dirs[-2] / "ndvi.tif"
        curr_ndvi = date_dirs[-1] / "ndvi.tif"
        if prev_ndvi.exists() and curr_ndvi.exists():
            art = create_before_after_png(
                prev_ndvi,
                curr_ndvi,
                out_dir / f"ndvi_{date_dirs[-2].name}_vs_{date_dirs[-1].name}.png",
                aoi_id,
                "ndvi_before_after",
            )
            if art:
                artifacts.append(art)

    # Fallback: consecutive normalized Sentinel-2 items
    if not artifacts:
        s2_root = settings.resolve_data_path(f"processed/sentinel-2-l2a/{aoi_id}")
        if s2_root.exists():
            norms = sorted(s2_root.glob("*/normalized.tif"), key=lambda p: p.parent.name)
            if len(norms) >= 2:
                art = create_before_after_png(
                    norms[-2],
                    norms[-1],
                    out_dir / f"optical_{norms[-2].parent.name}_vs_{norms[-1].parent.name}.png",
                    aoi_id,
                    "optical_before_after",
                )
                if art:
                    artifacts.append(art)

    return artifacts
