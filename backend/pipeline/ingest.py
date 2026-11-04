"""Pipeline step: curated Sentinel ingestion."""

from backend.ingestion.ingest import run_ingestion
from backend.shared.logging import get_logger

logger = get_logger(__name__)


def run_ingest_step(run_id: str) -> int:
    """
    Execute ingest step. Returns 0 on success, 1 if any asset failed.
    """
    result = run_ingestion(run_id=run_id)
    if result.assets_failed > 0:
        logger.warning(
            "ingest_step_partial_failure",
            failed=result.assets_failed,
            total=result.assets_total,
        )
        return 1
    return 0
