"""
GDELT DOC API ingestion.

Uses public GDELT 2.0 doc API (HTTPS). Falls back to curated local events when offline.
"""

import hashlib
from datetime import datetime, timezone
from typing import Any

from backend.osint.client import fetch_json, save_events_json
from backend.osint.models import OsintEvent, OsintSource
from backend.shared.config import get_settings
from backend.shared.logging import get_logger

logger = get_logger(__name__)

GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


def _parse_gdelt_article(article: dict[str, Any], idx: int) -> dict[str, Any] | None:
    """Normalize GDELT article to event dict."""
    try:
        lat = float(article.get("lat") or article.get("latitude") or 0)
        lon = float(article.get("lon") or article.get("longitude") or 0)
    except (TypeError, ValueError):
        return None
    if lat == 0 and lon == 0:
        return None
    title = str(article.get("title", ""))[:500]
    dt_str = article.get("seendate") or article.get("date")
    if not dt_str:
        return None
    try:
        if len(str(dt_str)) == 8:
            dt = datetime.strptime(str(dt_str), "%Y%m%d").replace(tzinfo=timezone.utc)
        else:
            dt = datetime.fromisoformat(str(dt_str).replace("Z", "+00:00"))
    except ValueError:
        dt = datetime.now(timezone.utc)
    text = f"{title} {article.get('domain', '')}".lower()
    words = [w for w in text.split() if len(w) > 3][:20]
    eid = hashlib.sha256(f"{title}{lat}{lon}{dt.isoformat()}".encode()).hexdigest()[:16]
    return {
        "event_id": f"gdelt-{eid}",
        "source": OsintSource.GDELT.value,
        "title": title,
        "summary": title,
        "datetime": dt.isoformat(),
        "latitude": lat,
        "longitude": lon,
        "keywords": words,
        "raw": {"domain": article.get("domain")},
    }


def fetch_gdelt_events(
    query: str,
    start_date: str,
    end_date: str,
    max_records: int = 50,
) -> list[dict[str, Any]]:
    """
    Query GDELT doc API.

    Dates in YYYYMMDDHHMMSS format for API.
    """
    params = {
        "query": query[:200],
        "mode": "ArtList",
        "maxrecords": min(max_records, 250),
        "format": "json",
        "startdatetime": f"{start_date}000000",
        "enddatetime": f"{end_date}235959",
    }
    data = fetch_json(GDELT_DOC_URL, params=params)
    articles = data.get("articles", data.get("article", []))
    if isinstance(articles, dict):
        articles = [articles]
    events = []
    for i, art in enumerate(articles or []):
        if not isinstance(art, dict):
            continue
        parsed = _parse_gdelt_article(art, i)
        if parsed:
            events.append(parsed)
    return events


def ingest_gdelt(keywords: list[str], use_live: bool = True) -> tuple[list[OsintEvent], str]:
    """Ingest GDELT events; save JSON under data/raw/osint/gdelt/."""
    settings = get_settings()
    out_path = settings.resolve_data_path("raw/osint/gdelt/events.json")
    curated_path = settings.resolve_data_path("raw/osint/gdelt/events_curated.json")

    raw_events: list[dict[str, Any]] = []

    if not settings.osint_live_fetch_enabled and curated_path.exists():
        import json

        raw_events = json.loads(curated_path.read_text(encoding="utf-8")).get("events", [])
        logger.info("gdelt_curated_mode", count=len(raw_events))
    elif use_live and settings.osint_live_fetch_enabled:
        try:
            from backend.osint.temporal import window_for_scope

            start, end = window_for_scope(settings.time_range_days)
            query = " OR ".join(keywords[:8])
            raw_events = fetch_gdelt_events(
                query,
                start.strftime("%Y%m%d"),
                end.strftime("%Y%m%d"),
                max_records=settings.osint_max_events_per_source,
            )
            logger.info("gdelt_live_fetch", count=len(raw_events))
        except Exception as exc:
            logger.warning("gdelt_live_fetch_failed", error=type(exc).__name__)

    if not raw_events and curated_path.exists():
        import json

        raw_events = json.loads(curated_path.read_text(encoding="utf-8")).get("events", [])
        logger.info("gdelt_curated_fallback", count=len(raw_events))

    save_events_json(out_path, raw_events)
    events = [OsintEvent.model_validate(e) for e in raw_events]
    return events, str(out_path.relative_to(settings.data_root)).replace("\\", "/")


def events_to_models(raw: list[dict[str, Any]]) -> list[OsintEvent]:
    return [OsintEvent.model_validate(e) for e in raw]
