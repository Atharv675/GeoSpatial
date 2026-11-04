"""
GeoJSON overlay generation for lightweight GIS (Leaflet).

Produces FeatureCollections for AOI boundary, OSINT markers, and anomaly summary.
"""

import json
from pathlib import Path
from typing import Any

from backend.explainability.models import ArtifactType, ExplainabilityArtifact
from backend.ingestion.aoi import aoi_to_feature, get_aoi
from backend.shared.config import get_settings
from backend.shared.logging import get_logger

logger = get_logger(__name__)


def _rel(path: Path) -> str:
    return str(path.relative_to(get_settings().data_root)).replace("\\", "/")


def _write_geojson(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def aoi_boundary_overlay(aoi_id: str, output_path: Path) -> ExplainabilityArtifact | None:
    aoi = get_aoi(aoi_id)
    if not aoi:
        return None
    fc = {"type": "FeatureCollection", "features": [aoi_to_feature(aoi)]}
    _write_geojson(output_path, fc)
    return ExplainabilityArtifact(
        type=ArtifactType.OVERLAY,
        aoi_id=aoi_id,
        name="aoi_boundary",
        path=_rel(output_path),
        description="AOI polygon boundary",
    )


def osint_markers_overlay(
    aoi_id: str,
    correlation_report: dict[str, Any],
    output_path: Path,
) -> ExplainabilityArtifact:
    features = []
    for match in correlation_report.get("matches", []):
        # Approximate location from title only if lat/lon not in match — load from raw osint
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [0, 0]},
                "properties": {
                    "event_id": match.get("event_id"),
                    "source": match.get("source"),
                    "confidence": match.get("confidence"),
                    "title": match.get("title", "")[:120],
                    "explanation": match.get("explanation", ""),
                },
            }
        )

    # Enrich with coordinates from raw OSINT store
    settings = get_settings()
    events_by_id: dict[str, dict] = {}
    for source in ("gdelt", "firms", "acled"):
        path = settings.resolve_data_path(f"raw/osint/{source}/events.json")
        if path.exists():
            for ev in json.loads(path.read_text(encoding="utf-8")).get("events", []):
                events_by_id[ev.get("event_id", "")] = ev

    for feat in features:
        ev = events_by_id.get(feat["properties"].get("event_id", ""))
        if ev:
            feat["geometry"] = {
                "type": "Point",
                "coordinates": [ev["longitude"], ev["latitude"]],
            }

    features = [f for f in features if f["geometry"]["coordinates"] != [0, 0]]
    fc = {"type": "FeatureCollection", "features": features}
    _write_geojson(output_path, fc)
    return ExplainabilityArtifact(
        type=ArtifactType.OVERLAY,
        aoi_id=aoi_id,
        name="osint_markers",
        path=_rel(output_path),
        description="OSINT events correlated with anomaly",
        metadata={"count": len(features)},
    )


def anomaly_summary_overlay(
    aoi_id: str,
    anomaly_report: dict[str, Any],
    output_path: Path,
) -> ExplainabilityArtifact:
    """GeoJSON overlay with anomaly properties on AOI for choropleth styling."""
    aoi = get_aoi(aoi_id)
    if not aoi:
        fc = {"type": "FeatureCollection", "features": []}
    else:
        feat = aoi_to_feature(aoi)
        feat["properties"] = {
            **feat["properties"],
            "composite_score": anomaly_report.get("composite_score", 0),
            "is_anomaly": anomaly_report.get("is_anomaly", False),
            "signals": [s.get("signal") for s in anomaly_report.get("signals", []) if s.get("triggered")],
        }
        fc = {"type": "FeatureCollection", "features": [feat]}
    _write_geojson(output_path, fc)
    return ExplainabilityArtifact(
        type=ArtifactType.OVERLAY,
        aoi_id=aoi_id,
        name="anomaly_summary",
        path=_rel(output_path),
        description="AOI styled with anomaly summary properties",
    )


def generate_aoi_overlays(
    aoi_id: str,
    run_id: str,
    anomaly_report: dict[str, Any] | None,
    correlation_report: dict[str, Any] | None,
) -> list[ExplainabilityArtifact]:
    settings = get_settings()
    out_dir = settings.resolve_data_path(f"explainability/{aoi_id}/{run_id}/overlays")
    artifacts: list[ExplainabilityArtifact] = []

    boundary = aoi_boundary_overlay(aoi_id, out_dir / "aoi_boundary.geojson")
    if boundary:
        artifacts.append(boundary)

    if anomaly_report:
        artifacts.append(anomaly_summary_overlay(aoi_id, anomaly_report, out_dir / "anomaly_summary.geojson"))

    if correlation_report and correlation_report.get("matches"):
        artifacts.append(
            osint_markers_overlay(aoi_id, correlation_report, out_dir / "osint_markers.geojson")
        )

    return artifacts
