"""Pipeline step: OSINT ingestion and correlation."""

from backend.osint.correlate import run_correlation
from backend.shared.logging import get_logger

logger = get_logger(__name__)


def run_correlate_osint_step(run_id: str) -> int:
    """Execute correlate_osint step. Returns 0 on success."""
    result = run_correlation(run_id=run_id)
    failed_ingest = sum(1 for r in result.ingest_results if r.status == "failed")
    if failed_ingest == len(result.ingest_results) and result.ingest_results:
        logger.warning("osint_all_ingest_failed")
        return 1
    return 0
