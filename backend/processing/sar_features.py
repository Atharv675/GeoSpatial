"""
SAR disturbance feature integration.

Uses Phase 3 SAR temporal difference rasters as surface disturbance evidence.
"""

from pathlib import Path
from shutil import copy2

from backend.shared.logging import get_logger

logger = get_logger(__name__)


def register_sar_disturbance(
    disturbance_path: Path,
    feature_output_path: Path,
) -> Path:
    """Copy/link SAR disturbance raster into features directory for scoring."""
    feature_output_path.parent.mkdir(parents=True, exist_ok=True)
    if disturbance_path.resolve() != feature_output_path.resolve():
        copy2(disturbance_path, feature_output_path)
    logger.info("sar_disturbance_registered", src=str(disturbance_path), dst=str(feature_output_path))
    return feature_output_path
