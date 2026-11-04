#!/usr/bin/env python3
"""Seed curated OSINT demo events for offline correlation (GDELT, FIRMS, ACLED)."""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw" / "osint"


def _events() -> dict[str, list[dict]]:
    now = datetime.now(timezone.utc)
    d = lambda days: (now - timedelta(days=days)).isoformat()

    return {
        "gdelt": [
            {
                "event_id": "gdelt-demo-001",
                "source": "gdelt",
                "title": "Wildfire smoke reported near eastern Mediterranean coast",
                "summary": "vegetation burn wildfire smoke levant region",
                "datetime": d(12),
                "latitude": 31.25,
                "longitude": 34.80,
                "keywords": ["wildfire", "burn", "vegetation", "smoke"],
                "raw": {"domain": "demo.gdelt"},
            },
            {
                "event_id": "gdelt-demo-002",
                "source": "gdelt",
                "title": "Flooding concerns after heavy rainfall in delta region",
                "summary": "flood water rainfall inundation agriculture",
                "datetime": d(8),
                "latitude": 30.06,
                "longitude": 31.18,
                "keywords": ["flood", "water", "rainfall"],
                "raw": {"domain": "demo.gdelt"},
            },
        ],
        "firms": [
            {
                "event_id": "firms-demo-001",
                "source": "firms",
                "title": "Active fire detection FRP=42.1",
                "summary": "FIRMS hotspot confidence=nominal",
                "datetime": d(11),
                "latitude": 31.22,
                "longitude": 34.78,
                "keywords": ["fire", "wildfire", "burn", "hotspot"],
                "raw": {"frp": "42.1", "confidence": "nominal"},
            },
            {
                "event_id": "firms-demo-002",
                "source": "firms",
                "title": "Active fire detection FRP=18.5",
                "summary": "FIRMS hotspot delta",
                "datetime": d(6),
                "latitude": 30.05,
                "longitude": 31.15,
                "keywords": ["fire", "hotspot"],
                "raw": {"frp": "18.5"},
            },
        ],
        "acled": [
            {
                "event_id": "acled-demo-001",
                "source": "acled",
                "title": "Protests and unrest near border area",
                "summary": "conflict protest unrest demonstration",
                "datetime": d(10),
                "latitude": 31.28,
                "longitude": 34.82,
                "keywords": ["conflict", "unrest", "protest"],
                "raw": {"event_type": "Protests", "fatalities": "0"},
            },
            {
                "event_id": "acled-demo-002",
                "source": "acled",
                "title": "Infrastructure disturbance reported",
                "summary": "construction activity disturbance infrastructure",
                "datetime": d(5),
                "latitude": 30.08,
                "longitude": 31.20,
                "keywords": ["infrastructure", "disturbance", "activity"],
                "raw": {"event_type": "Strategic developments"},
            },
        ],
    }


def main() -> int:
    events_by_source = _events()
    for source, events in events_by_source.items():
        out_dir = DATA / source
        out_dir.mkdir(parents=True, exist_ok=True)
        for name in ("events_curated.json", "events.json"):
            path = out_dir / name
            path.write_text(
                json.dumps({"events": events, "count": len(events)}, indent=2),
                encoding="utf-8",
            )
        print(f"  {source}: {len(events)} events")
    print(f"Wrote curated OSINT under {DATA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
