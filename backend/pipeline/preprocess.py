"""Pipeline step: raster preprocessing."""

from backend.preprocessing.preprocess import run_preprocessing
from backend.shared.logging import get_logger

logger = get_logger(__name__)


def run_preprocess_step(run_id: str) -> int:
    """Execute preprocess step. Returns 0 on success, 1 on any item failure."""
    result = run_preprocessing(run_id=run_id)
    if result.items_failed > 0:
        logger.warning(
            "preprocess_step_partial_failure",
            failed=result.items_failed,
            total=result.items_total,
        )
        return 1
    from backend.preprocessing.models import PreprocessStatus

    sar_failed = sum(1 for d in result.sar_diffs if d.status == PreprocessStatus.FAILED)
    if sar_failed:
        return 1
    return 0
