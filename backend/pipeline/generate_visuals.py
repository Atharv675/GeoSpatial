"""Pipeline step: explainability visual generation."""

from backend.explainability.generate import run_explainability
from backend.shared.logging import get_logger

logger = get_logger(__name__)


def run_generate_visuals_step(run_id: str) -> int:
    """Execute generate_visuals step. Returns 0 on success."""
    result = run_explainability(run_id=run_id)
    if result.artifacts_total == 0:
        logger.warning("explainability_no_artifacts", run_id=run_id)
    return 0
