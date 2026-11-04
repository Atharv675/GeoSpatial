"""
Deterministic pipeline orchestrator.

Execution order (explicit, reproducible):
  ingest → preprocess → analyze → correlate_osint → generate_alerts → generate_visuals

Phase 1: stub that logs steps; full implementation in Phases 2–8.
"""

import sys
from datetime import datetime, timezone

from backend.shared.logging import configure_logging, get_logger

logger = get_logger(__name__)

PIPELINE_STEPS = [
    "ingest",
    "preprocess",
    "analyze",
    "correlate_osint",
    "generate_alerts",
    "generate_visuals",
]


def run_pipeline() -> int:
    """Run the full pipeline sequence. Returns exit code."""
    from backend.shared.config import get_settings

    settings = get_settings()
    configure_logging(settings.log_level, settings.app_env)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    logger.info("pipeline_start", run_id=run_id, steps=PIPELINE_STEPS)

    exit_code = 0
    for step in PIPELINE_STEPS:
        logger.info("pipeline_step_start", step=step, run_id=run_id)
        if step == "ingest":
            from backend.pipeline.ingest import run_ingest_step

            step_code = run_ingest_step(run_id)
            if step_code != 0:
                exit_code = step_code
        elif step == "preprocess":
            from backend.pipeline.preprocess import run_preprocess_step

            step_code = run_preprocess_step(run_id)
            if step_code != 0:
                exit_code = step_code
        elif step == "analyze":
            from backend.pipeline.analyze import run_analyze_step

            step_code = run_analyze_step(run_id)
            if step_code != 0:
                exit_code = step_code
        elif step == "correlate_osint":
            from backend.pipeline.correlate_osint import run_correlate_osint_step

            step_code = run_correlate_osint_step(run_id)
            if step_code != 0:
                exit_code = step_code
        elif step == "generate_alerts":
            from backend.pipeline.generate_alerts import run_generate_alerts_step

            step_code = run_generate_alerts_step(run_id)
            if step_code != 0:
                exit_code = step_code
        elif step == "generate_visuals":
            from backend.pipeline.generate_visuals import run_generate_visuals_step

            step_code = run_generate_visuals_step(run_id)
            if step_code != 0:
                exit_code = step_code
        else:
            logger.info("pipeline_step", step=step, status="unknown_step")

    logger.info("pipeline_complete", run_id=run_id, exit_code=exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(run_pipeline())
