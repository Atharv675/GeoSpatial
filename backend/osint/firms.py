"""
NASA FIRMS active fire ingestion.

Requires FIRMS_MAP_KEY in environment. Uses curated fallback when unavailable.
"""

import csv
import hashlib
import io
from datetime import datetime, timezone

from backend.osint.client import fetch_text, save_events_json
from backend.osint.models import OsintEvent, OsintSource
from backend.shared.config import get_settings
from backend.shared.logging import get_logger

logger = get_logger(__name__)

FIRMS_AREA_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


def _parse_firms_csv(csv_text: str) -> list[dict]:
    """Parse FIRMS CSV rows to normalized events."""
    events = []
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        try:
            lat = float(row.get("latitude", row.get("lat", 0)))
            lon = float(row.get("longitude", row.get("lon", 0)))
        except (TypeError, ValueError):
            continue
        acq_date = row.get("acq_date", "")
        acq_time = row.get("acq_time", "0000")
        try:
            dt = datetime.strptime(f"{acq_date}{acq_time:0>4}", "%Y%m%d%H%M").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            dt = datetime.now(timezone.utc)
        frp = row.get("frp", "")
        eid = hashlib.sha256(f"{lat}{lon}{dt.isoformat()}".encode()).hexdigest()[:16]
        events.append(
            {
                "event_id": f"firms-{eid}",
                "source": OsintSource.FIRMS.value,
                "title": f"Active fire detection FRP={frp}",
                "summary": f"FIRMS hotspot confidence={row.get('confidence', '')}",
                "datetime": dt.isoformat(),
                "latitude": lat,
                "longitude": lon,
                "keywords": ["fire", "wildfire", "burn", "hotspot"],
                "raw": {"frp": frp, "confidence": row.get("confidence")},
            }
        )
    return events


def fetch_firms_area(
    api_key: str,
    west: float,
    south: float,
    east: float,
    north: float,
    day_range: int = 7,
    source: str = "VIIRS_SNPP_NRT",
) -> list[dict]:
    """Fetch FIRMS CSV for bounding box."""
    url = f"{FIRMS_AREA_URL}/{api_key}/{source}/{west},{south},{east},{north}/{day_range}"
    text = fetch_text(url)
    return _parse_firms_csv(text)


def ingest_firms(bbox: list[float], day_range: int = 7) -> tuple[list[OsintEvent], str]:
    """Ingest FIRMS events for AOI union bbox."""
    settings = get_settings()
    out_path = settings.resolve_data_path("raw/osint/firms/events.json")
    curated_path = settings.resolve_data_path("raw/osint/firms/events_curated.json")
    west, south, east, north = bbox
    raw_events: list[dict] = []

    if not settings.osint_live_fetch_enabled and curated_path.exists():
        import json

        raw_events = json.loads(curated_path.read_text(encoding="utf-8")).get("events", [])
        logger.info("firms_curated_mode", count=len(raw_events))
    elif settings.firms_map_key and settings.osint_live_fetch_enabled:
        try:
            raw_events = fetch_firms_area(
                settings.firms_map_key,
                west,
                south,
                east,
                north,
                day_range=min(day_range, settings.time_range_days),
            )
            logger.info("firms_live_fetch", count=len(raw_events))
        except Exception as exc:
            logger.warning("firms_live_fetch_failed", error=type(exc).__name__)

    if not raw_events and curated_path.exists():
        import json

        raw_events = json.loads(curated_path.read_text(encoding="utf-8")).get("events", [])
        logger.info("firms_curated_fallback", count=len(raw_events))

    save_events_json(out_path, raw_events[: settings.osint_max_events_per_source])
    return [OsintEvent.model_validate(e) for e in raw_events], str(
        out_path.relative_to(settings.data_root)
    ).replace("\\", "/")

