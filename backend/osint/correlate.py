"""
OSINT correlation orchestrator — ingest feeds and fuse with Phase 4 anomalies.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.ingestion.aoi import aoi_bbox, get_active_aois, get_aoi
from backend.osint.acled import ingest_acled
from backend.osint.firms import ingest_firms
from backend.osint.gdelt import ingest_gdelt
from backend.osint.keywords import extract_keywords_from_anomaly_report
from backend.osint.models import (
    AOICorrelationReport,
    CorrelationResult,
    OsintEvent,
    OsintIngestResult,
    OsintSource,
)
from backend.osint.scoring import correlate_event, fusion_confidence
from backend.osint.temporal import reference_datetime_from_date_key, window_for_scope
from backend.shared.config import get_settings
from backend.shared.logging import get_logger

logger = get_logger(__name__)

STATE_FILENAME = "correlation_state.json"


def _state_path() -> Path:
    return get_settings().resolve_data_path("processed/osint") / STATE_FILENAME


def _load_state() -> dict[str, Any]:
    path = _state_path()
    if not path.exists():
        return {"runs": []}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _save_state(state: dict[str, Any]) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def _union_bbox() -> list[float]:
    """Bounding box covering all active AOIs."""
    west, south, east, north = 180.0, 90.0, -180.0, -90.0
    for aoi in get_active_aois():
        w, s, e, n = aoi_bbox(aoi)
        west = min(west, w)
        south = min(south, s)
        east = max(east, e)
        north = max(north, n)
    return [west, south, east, north]


def _load_all_events() -> list[OsintEvent]:
    settings = get_settings()
    events: list[OsintEvent] = []
    for source in OsintSource:
        path = settings.resolve_data_path(f"raw/osint/{source.value}/events.json")
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for raw in data.get("events", []):
            try:
                events.append(OsintEvent.model_validate(raw))
            except Exception:
                continue
    return events


def _load_anomaly_reports() -> list[tuple[str, dict[str, Any]]]:
    """Load Phase 4 anomaly report JSON files."""
    settings = get_settings()
    reports: list[tuple[str, dict]] = []
    root = settings.resolve_data_path("processed/anomalies")
    if not root.exists():
        return reports
    for aoi_dir in root.iterdir():
        if not aoi_dir.is_dir():
            continue
        for report_file in sorted(aoi_dir.glob("report_*.json")):
            try:
                data = json.loads(report_file.read_text(encoding="utf-8"))
                reports.append((aoi_dir.name, data))
            except json.JSONDecodeError:
                continue
    return reports


def run_osint_ingestion() -> list[OsintIngestResult]:
    """Fetch or load curated OSINT from GDELT, FIRMS, ACLED."""
    settings = get_settings()
    start, end = window_for_scope(settings.time_range_days)
    keywords = ["fire", "flood", "conflict", "vegetation", "unrest"]
    results: list[OsintIngestResult] = []

    try:
        _, path = ingest_gdelt(keywords)
        count = len(json.loads(settings.resolve_data_path(path).read_text()).get("events", []))
        results.append(
            OsintIngestResult(
                source=OsintSource.GDELT,
                events_count=count,
                status="ok",
                storage_path=path,
            )
        )
    except Exception as exc:
        results.append(
            OsintIngestResult(
                source=OsintSource.GDELT,
                events_count=0,
                status="failed",
                message=str(exc)[:300],
            )
        )

    try:
        _, path = ingest_firms(_union_bbox(), day_range=settings.osint_correlation_window_days)
        count = len(json.loads(settings.resolve_data_path(path).read_text()).get("events", []))
        results.append(
            OsintIngestResult(
                source=OsintSource.FIRMS,
                events_count=count,
                status="ok",
                storage_path=path,
            )
        )
    except Exception as exc:
        results.append(
            OsintIngestResult(
                source=OsintSource.FIRMS,
                events_count=0,
                status="failed",
                message=str(exc)[:300],
            )
        )

    try:
        _, path = ingest_acled(
            start.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d"),
        )
        count = len(json.loads(settings.resolve_data_path(path).read_text()).get("events", []))
        results.append(
            OsintIngestResult(
                source=OsintSource.ACLED,
                events_count=count,
                status="ok",
                storage_path=path,
            )
        )
    except Exception as exc:
        results.append(
            OsintIngestResult(
                source=OsintSource.ACLED,
                events_count=0,
                status="failed",
                message=str(exc)[:300],
            )
        )

    return results


def run_correlation(run_id: str | None = None) -> CorrelationResult:
    """Full OSINT ingest + correlate with anomaly reports."""
    started = datetime.now(timezone.utc)
    run_id = run_id or started.strftime("%Y%m%dT%H%M%SZ")
    settings = get_settings()

    logger.info("osint_correlation_start", run_id=run_id)
    ingest_results = run_osint_ingestion()
    all_events = _load_all_events()
    anomaly_reports = _load_anomaly_reports()

    correlation_reports: list[AOICorrelationReport] = []
    total_matches = 0

    for aoi_id, report in anomaly_reports:
        aoi = get_aoi(aoi_id)
        if not aoi:
            continue
        bbox = aoi_bbox(aoi)
        keywords = extract_keywords_from_anomaly_report(report)
        date_key = str(report.get("datetime", "unknown"))
        try:
            ref_dt = reference_datetime_from_date_key(date_key)
        except ValueError:
            ref_dt = datetime.now(timezone.utc)

        matches = []
        for event in all_events:
            match = correlate_event(
                event,
                keywords,
                aoi.geometry,
                bbox,
                ref_dt,
            )
            if match:
                matches.append(match)

        matches.sort(key=lambda m: m.confidence, reverse=True)
        matches = matches[: settings.osint_max_matches_per_aoi]
        fusion, sources = fusion_confidence(matches)
        total_matches += len(matches)

        corr_report = AOICorrelationReport(
            aoi_id=aoi_id,
            anomaly_date=date_key,
            anomaly_composite_score=report.get("composite_score", 0.0),
            anomaly_is_triggered=report.get("is_anomaly", False),
            keywords_used=keywords,
            matches=matches,
            fusion_confidence=fusion,
            sources_agreeing=sources,
        )
        correlation_reports.append(corr_report)

        out_dir = settings.resolve_data_path(f"processed/osint/correlations/{aoi_id}")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"correlation_{run_id}.json"
        out_file.write_text(
            json.dumps(corr_report.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

    completed = datetime.now(timezone.utc)
    result = CorrelationResult(
        run_id=run_id,
        started_at=started,
        completed_at=completed,
        ingest_results=ingest_results,
        reports=correlation_reports,
        total_matches=total_matches,
        metadata={
            "events_loaded": len(all_events),
            "anomaly_reports": len(anomaly_reports),
            "correlation_window_days": settings.osint_correlation_window_days,
        },
    )

    state = _load_state()
    state.setdefault("runs", []).append(
        {"run_id": run_id, "total_matches": total_matches, "reports": len(correlation_reports)}
    )
    state["last_run"] = result.model_dump(mode="json")
    _save_state(state)

    logger.info(
        "osint_correlation_complete",
        run_id=run_id,
        matches=total_matches,
        reports=len(correlation_reports),
    )
    return result


def get_last_correlation_summary() -> dict[str, Any] | None:
    return _load_state().get("last_run")
