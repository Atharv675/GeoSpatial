"""
Confidence breakdown assembly for analyst review.

Merges Phase 4 anomaly signals and Phase 5 OSINT fusion into one document.
"""

import json
from pathlib import Path
from typing import Any

from backend.explainability.models import ArtifactType, ExplainabilityArtifact
from backend.shared.config import get_settings
from backend.shared.logging import get_logger

logger = get_logger(__name__)


def build_confidence_breakdown(
    aoi_id: str,
    anomaly_report: dict[str, Any] | None,
    correlation_report: dict[str, Any] | None,
) -> dict[str, Any]:
    """Merge geospatial and OSINT confidence evidence."""
    breakdown: dict[str, Any] = {
        "aoi_id": aoi_id,
        "summary": "Operational explainability — rule-based evidence only",
        "geospatial": {},
        "osint": {},
        "fusion": {},
    }

    if anomaly_report:
        breakdown["geospatial"] = {
            "composite_score": anomaly_report.get("composite_score", 0),
            "is_anomaly": anomaly_report.get("is_anomaly", False),
            "datetime": anomaly_report.get("datetime"),
            "signals": anomaly_report.get("signals", []),
            "evidence_paths": anomaly_report.get("evidence_paths", {}),
        }

    if correlation_report:
        breakdown["osint"] = {
            "fusion_confidence": correlation_report.get("fusion_confidence", 0),
            "sources_agreeing": correlation_report.get("sources_agreeing", []),
            "keywords_used": correlation_report.get("keywords_used", []),
            "top_matches": correlation_report.get("matches", [])[:5],
        }
        breakdown["fusion"] = {
            "combined_assessment": _combined_assessment(anomaly_report, correlation_report),
            "recommended_review": correlation_report.get("matches", [])[:3],
        }

    return breakdown


def _combined_assessment(
    anomaly: dict[str, Any] | None,
    osint: dict[str, Any] | None,
) -> str:
    geo_flag = anomaly.get("is_anomaly", False) if anomaly else False
    osint_conf = osint.get("fusion_confidence", 0) if osint else 0
    if geo_flag and osint_conf >= 0.5:
        return "Geospatial anomaly corroborated by OSINT events in AOI and time window"
    if geo_flag:
        return "Geospatial anomaly detected; limited OSINT corroboration"
    if osint_conf >= 0.5:
        return "OSINT activity in region without strong geospatial anomaly flag"
    return "No strong fused signal in current window"


def save_confidence_breakdown(
    aoi_id: str,
    run_id: str,
    breakdown: dict[str, Any],
) -> ExplainabilityArtifact:
    settings = get_settings()
    path = settings.resolve_data_path(
        f"explainability/{aoi_id}/{run_id}/confidence_breakdown.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(breakdown, indent=2), encoding="utf-8")
    rel = str(path.relative_to(settings.data_root)).replace("\\", "/")
    return ExplainabilityArtifact(
        type=ArtifactType.CONFIDENCE,
        aoi_id=aoi_id,
        name="confidence_breakdown",
        path=rel,
        description="Merged geospatial + OSINT confidence breakdown",
    )
