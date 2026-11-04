"""Live Seismic Telemetry Router (USGS Earthquakes).

Proxies USGS real-time seismic GeoJSON with singleflight caching.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException

from backend.services.singleflight import is_allowed_host, safe_http_get, singleflight
from backend.shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/live", tags=["live-earthquakes"])

USGS_ALL_DAY_GEOJSON = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"

FALLBACK_QUAKES = [
    {
        "id": "us7000m999",
        "magnitude": 5.4,
        "place": "12 km SW of Antakya, Turkey",
        "time": int(time.time() * 1000) - 3600000,
        "latitude": 36.12,
        "longitude": 36.08,
        "depth_km": 10.0,
        "tsunami": 0,
        "alert": "green",
    },
    {
        "id": "nc74001234",
        "magnitude": 4.1,
        "place": "18 km E of Ridgecrest, CA",
        "time": int(time.time() * 1000) - 7200000,
        "latitude": 35.65,
        "longitude": -117.48,
        "depth_km": 8.5,
        "tsunami": 0,
        "alert": None,
    },
]


@router.get("/earthquakes")
async def get_live_earthquakes() -> Dict[str, Any]:
    """Ingest USGS 24-hour seismic event GeoJSON, cached for 60 seconds."""
    cache_key = "earthquakes:all_day"

    async def _fetch() -> Dict[str, Any]:
        data = await safe_http_get(USGS_ALL_DAY_GEOJSON, timeout=8.0, as_json=True)
        features = data.get("features") or []
        normalized: List[Dict[str, Any]] = []

        for f in features:
            props = f.get("properties") or {}
            geom = f.get("geometry") or {}
            coords = geom.get("coordinates") or []
            if len(coords) < 2:
                continue

            lon = coords[0]
            lat = coords[1]
            depth = coords[2] if len(coords) > 2 else 0.0

            normalized.append({
                "id": f.get("id"),
                "magnitude": props.get("mag"),
                "place": props.get("place"),
                "time": props.get("time"),
                "latitude": float(lat),
                "longitude": float(lon),
                "depth_km": float(depth),
                "tsunami": props.get("tsunami", 0),
                "alert": props.get("alert"),
            })

        return {
            "count": len(normalized),
            "earthquakes": normalized,
            "geojson": data,
            "source": "usgs",
            "timestamp": time.time(),
        }

    try:
        return await singleflight.execute(cache_key, _fetch, ttl_seconds=60.0, allow_stale_on_error=True)
    except Exception as e:
        logger.warning("usgs_earthquakes_fetch_failed", error=str(e))
        return {
            "count": len(FALLBACK_QUAKES),
            "earthquakes": FALLBACK_QUAKES,
            "source": "fallback_seed",
            "timestamp": time.time(),
        }
