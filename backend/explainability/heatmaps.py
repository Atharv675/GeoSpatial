"""
Heatmap generation from processed rasters and feature layers.
"""

from pathlib import Path

import rasterio

from backend.explainability.colormap import raster_to_heatmap_png
from backend.explainability.models import ArtifactType, ExplainabilityArtifact
from backend.shared.config import get_settings
from backend.shared.logging import get_logger

logger = get_logger(__name__)


def _rel(path: Path) -> str:
    return str(path.relative_to(get_settings().data_root)).replace("\\", "/")


def heatmap_from_geotiff(
    src_path: Path,
    output_path: Path,
    aoi_id: str,
    name: str,
    description: str,
) -> ExplainabilityArtifact | None:
    """Create PNG heatmap from GeoTIFF."""
    if not src_path.exists():
        return None
    try:
        with rasterio.open(src_path) as src:
            data = src.read(1).astype("float32")
        raster_to_heatmap_png(data, output_path, max_width=get_settings().explainability_png_width)
        logger.info("heatmap_created", name=name, aoi_id=aoi_id)
        return ExplainabilityArtifact(
            type=ArtifactType.HEATMAP,
            aoi_id=aoi_id,
            name=name,
            path=_rel(output_path),
            description=description,
            metadata={"source": _rel(src_path)},
        )
    except Exception as exc:
        logger.warning("heatmap_failed", name=name, error=type(exc).__name__)
        return None


def generate_aoi_heatmaps(aoi_id: str, run_id: str) -> list[ExplainabilityArtifact]:
    """Generate standard heatmaps for an AOI from processed outputs."""
    settings = get_settings()
    out_dir = settings.resolve_data_path(f"explainability/{aoi_id}/{run_id}/heatmaps")
    artifacts: list[ExplainabilityArtifact] = []

    candidates = [
        ("anomaly_score", f"processed/anomalies/{aoi_id}/anomaly_score_*.tif", "Composite anomaly score"),
        ("sar_disturbance", f"processed/features/{aoi_id}/sar", "SAR temporal disturbance"),
        ("ndvi_temporal", f"processed/features/{aoi_id}/temporal", "NDVI temporal change"),
    ]

    # Anomaly score — glob latest
    anom_root = settings.resolve_data_path(f"processed/anomalies/{aoi_id}")
    if anom_root.exists():
        scores = sorted(anom_root.glob("anomaly_score_*.tif"))
        if scores:
            art = heatmap_from_geotiff(
                scores[-1],
                out_dir / "anomaly_score.png",
                aoi_id,
                "anomaly_score",
                "Rule-based composite anomaly score",
            )
            if art:
                artifacts.append(art)

    sar_dir = settings.resolve_data_path(f"processed/features/{aoi_id}/sar")
    if sar_dir.exists():
        sar_files = sorted(sar_dir.glob("*_diff.tif"))
        if sar_files:
            art = heatmap_from_geotiff(
                sar_files[-1],
                out_dir / "sar_disturbance.png",
                aoi_id,
                "sar_disturbance",
                "Sentinel-1 temporal SAR difference",
            )
            if art:
                artifacts.append(art)

    temporal_dir = settings.resolve_data_path(f"processed/features/{aoi_id}/temporal")
    if temporal_dir.exists():
        for pattern, label in [("*ndvi*diff*", "ndvi_temporal"), ("*ndwi*diff*", "ndwi_temporal"), ("*nbr*diff*", "nbr_temporal")]:
            matches = sorted(temporal_dir.glob(pattern))
            if matches:
                art = heatmap_from_geotiff(
                    matches[-1],
                    out_dir / f"{label}.png",
                    aoi_id,
                    label,
                    f"Temporal difference: {label}",
                )
                if art:
                    artifacts.append(art)

    return artifacts
