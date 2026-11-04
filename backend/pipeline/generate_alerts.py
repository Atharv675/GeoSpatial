"""Pipeline step: operational alert generation."""

from backend.alerts.generate import generate_alerts
from backend.shared.logging import get_logger

logger = get_logger(__name__)


def run_generate_alerts_step(run_id: str) -> int:
    """Execute generate_alerts step. Returns 0 on success."""
    result = generate_alerts(run_id=run_id)
    if not result.alerts:
        logger.info("alerts_step_no_alerts", run_id=run_id)
    return 0
