"""
Explainability orchestrator — heatmaps, overlays, before/after, confidence, timelines.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.explainability.before_after import generate_before_after_pairs
from backend.explainability.confidence import build_confidence_breakdown, save_confidence_breakdown
from backend.explainability.heatmaps import generate_aoi_heatmaps
from backend.explainability.models import AOIExplainabilityBundle, ExplainabilityResult
from backend.explainability.overlays import generate_aoi_overlays
from backend.explainability.timelines import build_timeline, save_timeline
from backend.ingestion.aoi import get_active_aois
from backend.shared.config import get_settings
from backend.shared.logging import get_logger

logger = get_logger(__name__)

STATE_FILENAME = "explainability_state.json"


def _state_path() -> Path:
    return get_settings().resolve_data_path("explainability") / STATE_FILENAME


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _latest_anomaly_report(aoi_id: str) -> dict[str, Any] | None:
    root = get_settings().resolve_data_path(f"processed/anomalies/{aoi_id}")
    if not root.exists():
        return None
    reports = sorted(root.glob("report_*.json"))
    return _load_json(reports[-1]) if reports else None


def _latest_correlation_report(aoi_id: str) -> dict[str, Any] | None:
    root = get_settings().resolve_data_path(f"processed/osint/correlations/{aoi_id}")
    if not root.exists():
        return None
    reports = sorted(root.glob("correlation_*.json"))
    return _load_json(reports[-1]) if reports else None


def _save_manifest(bundle: AOIExplainabilityBundle) -> None:
    settings = get_settings()
    path = settings.resolve_data_path(
        f"explainability/{bundle.aoi_id}/{bundle.run_id}/manifest.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bundle.model_dump(mode="json"), indent=2), encoding="utf-8")


def generate_aoi_explainability(aoi_id: str, run_id: str) -> AOIExplainabilityBundle:
    """Generate full explainability bundle for one AOI."""
    anomaly = _latest_anomaly_report(aoi_id)
    correlation = _latest_correlation_report(aoi_id)

    artifacts = []
    artifacts.extend(generate_aoi_heatmaps(aoi_id, run_id))
    artifacts.extend(generate_aoi_overlays(aoi_id, run_id, anomaly, correlation))
    artifacts.extend(generate_before_after_pairs(aoi_id, run_id))

    breakdown = build_confidence_breakdown(aoi_id, anomaly, correlation)
    artifacts.append(save_confidence_breakdown(aoi_id, run_id, breakdown))

    timeline = build_timeline(aoi_id, anomaly, correlation)
    artifacts.append(save_timeline(aoi_id, run_id, timeline))

    bundle = AOIExplainabilityBundle(
        aoi_id=aoi_id,
        run_id=run_id,
        artifacts=artifacts,
        timeline=timeline,
        confidence_breakdown=breakdown,
    )
    _save_manifest(bundle)
    logger.info(
        "explainability_aoi_complete",
        aoi_id=aoi_id,
        artifacts=len(artifacts),
    )
    return bundle


def run_explainability(run_id: str | None = None) -> ExplainabilityResult:
    """Generate explainability outputs for all active AOIs."""
    started = datetime.now(timezone.utc)
    run_id = run_id or started.strftime("%Y%m%dT%H%M%SZ")

    logger.info("explainability_start", run_id=run_id)
    bundles: list[AOIExplainabilityBundle] = []

    for aoi in get_active_aois():
        bundles.append(generate_aoi_explainability(aoi.aoi_id, run_id))

    completed = datetime.now(timezone.utc)
    total = sum(len(b.artifacts) for b in bundles)

    result = ExplainabilityResult(
        run_id=run_id,
        started_at=started,
        completed_at=completed,
        bundles=bundles,
        artifacts_total=total,
        metadata={"aois": len(bundles)},
    )

    state_path = _state_path()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state = {"last_run": result.model_dump(mode="json")}
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    logger.info("explainability_complete", run_id=run_id, artifacts=total)
    return result


def get_last_explainability() -> dict[str, Any] | None:
    path = _state_path()
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8")).get("last_run")
