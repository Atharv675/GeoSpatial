"""
Anomaly timeline generation for analyst workflows.
"""

import json
from pathlib import Path
from typing import Any

from backend.explainability.models import ArtifactType, ExplainabilityArtifact, TimelineEvent
from backend.shared.config import get_settings
from backend.shared.logging import get_logger

logger = get_logger(__name__)


def build_timeline(
    aoi_id: str,
    anomaly_report: dict[str, Any] | None,
    correlation_report: dict[str, Any] | None,
) -> list[TimelineEvent]:
    """Construct sorted timeline from anomaly and OSINT evidence."""
    events: list[TimelineEvent] = []

    if anomaly_report:
        events.append(
            TimelineEvent(
                datetime=str(anomaly_report.get("datetime", "")),
                label="Geospatial anomaly assessment",
                category="anomaly",
                score=float(anomaly_report.get("composite_score", 0)),
                source="geospatial",
            )
        )
        for sig in anomaly_report.get("signals", []):
            if sig.get("triggered"):
                events.append(
                    TimelineEvent(
                        datetime=str(anomaly_report.get("datetime", "")),
                        label=f"Signal: {sig.get('signal', 'unknown')}",
                        category="signal",
                        score=float(sig.get("value", 0)),
                        source="geospatial",
                    )
                )

    if correlation_report:
        for match in correlation_report.get("matches", [])[:10]:
            events.append(
                TimelineEvent(
                    datetime=str(match.get("datetime", "")),
                    label=match.get("title", "OSINT event")[:80],
                    category="osint",
                    score=float(match.get("confidence", 0)),
                    source=str(match.get("source", "osint")),
                )
            )

    events.sort(key=lambda e: e.datetime)
    return events


def save_timeline(
    aoi_id: str,
    run_id: str,
    timeline: list[TimelineEvent],
) -> ExplainabilityArtifact:
    settings = get_settings()
    path = settings.resolve_data_path(f"explainability/{aoi_id}/{run_id}/timeline.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"aoi_id": aoi_id, "events": [e.model_dump() for e in timeline]}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    rel = str(path.relative_to(settings.data_root)).replace("\\", "/")
    return ExplainabilityArtifact(
        type=ArtifactType.TIMELINE,
        aoi_id=aoi_id,
        name="timeline",
        path=rel,
        description="Chronological anomaly and OSINT timeline",
        metadata={"event_count": len(timeline)},
    )
