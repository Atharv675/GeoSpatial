"""
Rule-based operational alert generation from anomaly + OSINT fusion reports.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.alerts.models import AlertGenerationResult, AlertSeverity, OperationalAlert
from backend.ingestion.aoi import get_active_aois
from backend.shared.config import get_settings
from backend.shared.logging import get_logger

logger = get_logger(__name__)

STATE_FILENAME = "alerts_state.json"


def _state_path() -> Path:
    return get_settings().resolve_data_path("alerts") / STATE_FILENAME


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _latest_anomaly(aoi_id: str) -> dict[str, Any] | None:
    root = get_settings().resolve_data_path(f"processed/anomalies/{aoi_id}")
    if not root.exists():
        return None
    reports = sorted(root.glob("report_*.json"))
    return _load_json(reports[-1]) if reports else None


def _latest_correlation(aoi_id: str) -> dict[str, Any] | None:
    root = get_settings().resolve_data_path(f"processed/osint/correlations/{aoi_id}")
    if not root.exists():
        return None
    corrs = sorted(root.glob("correlation_*.json"))
    return _load_json(corrs[-1]) if corrs else None


def _severity(geo_score: float, osint_fusion: float, is_anomaly: bool) -> AlertSeverity:
    settings = get_settings()
    if is_anomaly and osint_fusion >= settings.alert_critical_osint_threshold:
        return AlertSeverity.CRITICAL
    if is_anomaly and geo_score >= settings.alert_high_geo_threshold:
        return AlertSeverity.HIGH
    if is_anomaly or osint_fusion >= settings.alert_medium_osint_threshold:
        return AlertSeverity.MEDIUM
    if geo_score >= settings.alert_low_geo_threshold:
        return AlertSeverity.LOW
    return AlertSeverity.LOW


def _build_alert(
    aoi_id: str,
    anomaly: dict[str, Any] | None,
    correlation: dict[str, Any] | None,
    run_id: str,
) -> OperationalAlert | None:
    geo_score = float(anomaly.get("composite_score", 0)) if anomaly else 0.0
    is_anomaly = bool(anomaly.get("is_anomaly", False)) if anomaly else False
    osint_fusion = float(correlation.get("fusion_confidence", 0)) if correlation else 0.0
    settings = get_settings()

    if not is_anomaly and osint_fusion < settings.alert_medium_osint_threshold:
        return None

    severity = _severity(geo_score, osint_fusion, is_anomaly)
    match_count = len(correlation.get("matches", [])) if correlation else 0
    title = f"{severity.value.upper()} — {aoi_id}"
    summary = (
        f"Geospatial composite {geo_score:.2f}; "
        f"OSINT fusion {osint_fusion:.2f}; "
        f"{match_count} correlated events"
    )

    return OperationalAlert(
        alert_id=f"{aoi_id}-{run_id}-{uuid4().hex[:8]}",
        aoi_id=aoi_id,
        severity=severity,
        title=title,
        summary=summary,
        geospatial_score=geo_score,
        osint_fusion_score=osint_fusion,
        is_anomaly=is_anomaly,
        created_at=datetime.now(timezone.utc),
        evidence={
            "anomaly_datetime": anomaly.get("datetime") if anomaly else None,
            "sources_agreeing": correlation.get("sources_agreeing", []) if correlation else [],
            "top_match_titles": [
                m.get("title", "")[:60] for m in (correlation or {}).get("matches", [])[:3]
            ],
        },
    )


def generate_alerts(run_id: str | None = None) -> AlertGenerationResult:
    """Create operational alerts for active AOIs."""
    started = datetime.now(timezone.utc)
    run_id = run_id or started.strftime("%Y%m%dT%H%M%SZ")
    settings = get_settings()

    logger.info("alerts_generation_start", run_id=run_id)
    alerts: list[OperationalAlert] = []
    aois = list(get_active_aois())

    for aoi in aois:
        anomaly = _latest_anomaly(aoi.aoi_id)
        correlation = _latest_correlation(aoi.aoi_id)
        alert = _build_alert(aoi.aoi_id, anomaly, correlation, run_id)
        if alert:
            alerts.append(alert)
            out = settings.resolve_data_path(f"alerts/{aoi.aoi_id}/alert_{run_id}.json")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(alert.model_dump(mode="json"), indent=2), encoding="utf-8")

    completed = datetime.now(timezone.utc)
    result = AlertGenerationResult(
        run_id=run_id,
        started_at=started,
        completed_at=completed,
        alerts=alerts,
        metadata={"aois_checked": len(aois)},
    )

    state_path = _state_path()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps({"last_run": result.model_dump(mode="json")}, indent=2),
        encoding="utf-8",
    )
    logger.info("alerts_generation_complete", run_id=run_id, count=len(alerts))
    return result


def get_last_alerts() -> dict[str, Any] | None:
    path = _state_path()
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8")).get("last_run")
