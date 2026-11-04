"""
ACLED conflict event ingestion.

Requires ACLED_EMAIL and ACLED_PASSWORD. Uses curated fallback when unavailable.
"""

import hashlib
from datetime import datetime, timezone
from typing import Any

from backend.osint.client import fetch_json, save_events_json
from backend.osint.models import OsintEvent, OsintSource
from backend.shared.config import get_settings
from backend.shared.logging import get_logger

logger = get_logger(__name__)

ACLED_API_URL = "https://api.acleddata.com/acled/read"


def _parse_acled_row(row: dict[str, Any]) -> dict[str, Any] | None:
    try:
        lat = float(row.get("latitude", 0))
        lon = float(row.get("longitude", 0))
    except (TypeError, ValueError):
        return None
    if lat == 0 and lon == 0:
        return None
    event_date = row.get("event_date", "")
    try:
        dt = datetime.strptime(str(event_date), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        dt = datetime.now(timezone.utc)
    title = str(row.get("event_type", "ACLED event"))[:200]
    notes = str(row.get("notes", ""))[:500]
    text = f"{title} {notes} {row.get('sub_event_type', '')}".lower()
    words = [w for w in text.split() if len(w) > 4][:15]
    eid = hashlib.sha256(f"{lat}{lon}{dt}{title}".encode()).hexdigest()[:16]
    return {
        "event_id": f"acled-{eid}",
        "source": OsintSource.ACLED.value,
        "title": title,
        "summary": notes or title,
        "datetime": dt.isoformat(),
        "latitude": lat,
        "longitude": lon,
        "keywords": words + ["conflict", "unrest"],
        "raw": {
            "event_type": row.get("event_type"),
            "fatalities": row.get("fatalities"),
        },
    }


def fetch_acled_events(
    email: str,
    password: str,
    country: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Fetch ACLED events via API (HTTPS)."""
    params: dict[str, Any] = {
        "email": email,
        "password": password,
        "limit": min(limit, 500),
    }
    if country:
        params["country"] = country
    if start_date:
        params["event_date"] = f"{start_date}|{end_date or start_date}"
    data = fetch_json(ACLED_API_URL, params=params)
    rows = data.get("data", [])
    events = []
    for row in rows:
        if isinstance(row, dict):
            parsed = _parse_acled_row(row)
            if parsed:
                events.append(parsed)
    return events


def ingest_acled(
    start_date: str,
    end_date: str,
    country: str | None = None,
) -> tuple[list[OsintEvent], str]:
    """Ingest ACLED with credential check and curated fallback."""
    settings = get_settings()
    out_path = settings.resolve_data_path("raw/osint/acled/events.json")
    curated_path = settings.resolve_data_path("raw/osint/acled/events_curated.json")
    raw_events: list[dict] = []

    if not settings.osint_live_fetch_enabled and curated_path.exists():
        import json

        raw_events = json.loads(curated_path.read_text(encoding="utf-8")).get("events", [])
        logger.info("acled_curated_mode", count=len(raw_events))
    elif (
        settings.acled_email
        and settings.acled_password
        and settings.osint_live_fetch_enabled
    ):
        try:
            raw_events = fetch_acled_events(
                settings.acled_email,
                settings.acled_password,
                country=country,
                start_date=start_date,
                end_date=end_date,
                limit=settings.osint_max_events_per_source,
            )
            logger.info("acled_live_fetch", count=len(raw_events))
        except Exception as exc:
            logger.warning("acled_live_fetch_failed", error=type(exc).__name__)

    if not raw_events and curated_path.exists():
        import json

        raw_events = json.loads(curated_path.read_text(encoding="utf-8")).get("events", [])
        logger.info("acled_curated_fallback", count=len(raw_events))

    save_events_json(out_path, raw_events[: settings.osint_max_events_per_source])
    return [OsintEvent.model_validate(e) for e in raw_events], str(
        out_path.relative_to(settings.data_root)
    ).replace("\\", "/")

