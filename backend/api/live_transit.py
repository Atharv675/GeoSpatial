"""Live Public Transit Vehicle Telemetry Router (GTFS-RT Protobuf).

Ingests and decodes GTFS-Realtime binary protobuf feeds from municipal transit agencies.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Path
from google.transit import gtfs_realtime_pb2

from backend.services.singleflight import is_allowed_host, safe_http_get, singleflight
from backend.shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/live", tags=["live-transit"])

AGENCY_ENDPOINTS = {
    "mbta": {
        "name": "MBTA (Boston)",
        "url": "https://cdn.mbta.com/realtime/VehiclePositions.pb",
        "city": "Boston, MA",
    },
    "hsl": {
        "name": "HSL (Helsinki)",
        "url": "https://realtime.hsl.fi/realtime/vehicle-positions/v2/hsl",
        "city": "Helsinki, Finland",
    },
}

FALLBACK_TRANSIT_VEHICLES = {
    "mbta": [
        {
            "id": "mbta-1740",
            "label": "Red Line Train 01740",
            "latitude": 42.3621,
            "longitude": -71.0845,
            "bearing": 90.0,
            "speed_kmh": 45.0,
            "route_id": "Red",
            "status": "IN_TRANSIT_TO",
        },
        {
            "id": "mbta-2204",
            "label": "Green Line Trolley 2204",
            "latitude": 42.3522,
            "longitude": -71.0634,
            "bearing": 210.0,
            "speed_kmh": 28.0,
            "route_id": "Green-D",
            "status": "STOPPED_AT",
        },
    ],
    "hsl": [
        {
            "id": "hsl-901",
            "label": "Tram 9 - Pasila",
            "latitude": 60.1988,
            "longitude": 24.9332,
            "bearing": 180.0,
            "speed_kmh": 22.0,
            "route_id": "9",
            "status": "IN_TRANSIT_TO",
        }
    ],
}


def decode_gtfs_rt(data: bytes, limit: int = 200) -> List[Dict[str, Any]]:
    """Decode GTFS-Realtime binary protobuf bytes into normalized dicts."""
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(data)

    vehicles = []
    for entity in feed.entity:
        if not entity.HasField("vehicle"):
            continue
        v = entity.vehicle
        pos = v.position
        if not pos.latitude or not pos.longitude:
            continue

        vehicles.append({
            "id": entity.id or v.vehicle.id or "v",
            "label": v.vehicle.label or v.vehicle.id or entity.id,
            "latitude": float(pos.latitude),
            "longitude": float(pos.longitude),
            "bearing": float(pos.bearing) if pos.bearing else None,
            "speed_kmh": round(float(pos.speed) * 3.6, 1) if pos.speed else None,
            "route_id": v.trip.route_id if v.HasField("trip") else None,
            "status": str(v.current_status) if v.current_status else "IN_TRANSIT_TO",
        })
        if len(vehicles) >= limit:
            break
    return vehicles


@router.get("/transit/vehicles/{agency_id}")
async def get_transit_vehicles(
    agency_id: str = Path(..., description="Agency ID e.g. mbta, hsl, ttc, capmetro")
) -> Dict[str, Any]:
    """Ingest and decode live GTFS-Realtime vehicle positions."""
    agency_key = agency_id.lower().strip()
    config = AGENCY_ENDPOINTS.get(agency_key)
    cache_key = f"transit:{agency_key}"

    if not config:
        # Check if fallback exists
        fallback = FALLBACK_TRANSIT_VEHICLES.get(agency_key, FALLBACK_TRANSIT_VEHICLES["mbta"])
        return {
            "agency": agency_key,
            "count": len(fallback),
            "vehicles": fallback,
            "source": "simulated",
        }

    url = config["url"]

    async def _fetch() -> Dict[str, Any]:
        raw_pb = await safe_http_get(url, timeout=8.0, as_json=False)
        vehicles = decode_gtfs_rt(raw_pb)
        return {
            "agency": config["name"],
            "city": config["city"],
            "count": len(vehicles),
            "vehicles": vehicles,
            "source": "gtfs_realtime",
            "timestamp": time.time(),
        }

    try:
        return await singleflight.execute(cache_key, _fetch, ttl_seconds=15.0, allow_stale_on_error=True)
    except Exception as e:
        logger.warning("transit_gtfs_fetch_failed", agency=agency_key, error=str(e))
        fallback = FALLBACK_TRANSIT_VEHICLES.get(agency_key, FALLBACK_TRANSIT_VEHICLES["mbta"])
        return {
            "agency": config["name"],
            "city": config["city"],
            "count": len(fallback),
            "vehicles": fallback,
            "source": "fallback_seed",
            "timestamp": time.time(),
        }
