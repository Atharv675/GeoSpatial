"""Pipeline step: feature engineering and anomaly analysis."""

from backend.processing.analyze import run_analysis
from backend.shared.logging import get_logger

logger = get_logger(__name__)


def run_analyze_step(run_id: str) -> int:
    """Execute analyze step. Returns 0 on success, 1 on failures."""
    result = run_analysis(run_id=run_id)
    if result.features_failed > 0:
        logger.warning(
            "analyze_step_partial_failure",
            failed=result.features_failed,
        )
        return 1
    return 0
