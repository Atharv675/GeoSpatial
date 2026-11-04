"""Live Aircraft Telemetry Router (OpenSky & ADS-B).

Provides real-time commercial and military tracking with automatic failover,
deduplication via singleflight cache, and aircraft enrichment.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.services.singleflight import is_allowed_host, singleflight
from backend.shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/live", tags=["live-aircraft"])


class AircraftRecord(BaseModel):
    icao24: str
    callsign: Optional[str] = None
    origin_country: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    baro_altitude: Optional[float] = None
    on_ground: bool = False
    velocity: Optional[float] = None
    true_track: Optional[float] = None
    vertical_rate: Optional[float] = None
    category: str = "civilian"


class AircraftResponse(BaseModel):
    aircraft: List[AircraftRecord]
    source: str
    count: int
    timestamp: float


# Fallback synthetic tracks for resilient presentation when both upstreams are rate-limited
SAMPLE_FALLBACK_AIRCRAFT = [
    AircraftRecord(
        icao24="ae5881",
        callsign="FORTE10",
        origin_country="United States",
        longitude=31.42,
        latitude=34.85,
        baro_altitude=16200,
        on_ground=False,
        velocity=180.2,
        true_track=85.0,
        vertical_rate=0.0,
        category="reconnaissance",
    ),
    AircraftRecord(
        icao24="4b1812",
        callsign="THY1821",
        origin_country="Turkey",
        longitude=29.01,
        latitude=41.12,
        baro_altitude=11270,
        on_ground=False,
        velocity=235.0,
        true_track=240.0,
        vertical_rate=-2.5,
        category="commercial",
    ),
    AircraftRecord(
        icao24="3c65c2",
        callsign="DLH400",
        origin_country="Germany",
        longitude=-73.78,
        latitude=40.64,
        baro_altitude=9800,
        on_ground=False,
        velocity=245.8,
        true_track=72.0,
        vertical_rate=5.0,
        category="commercial",
    ),
    AircraftRecord(
        icao24="a10bf2",
        callsign="RCH814",
        origin_country="United States",
        longitude=14.28,
        latitude=37.15,
        baro_altitude=8500,
        on_ground=False,
        velocity=210.0,
        true_track=115.0,
        vertical_rate=0.0,
        category="military_transport",
    ),
]


async def fetch_opensky(
    lamin: Optional[float],
    lomin: Optional[float],
    lamax: Optional[float],
    lomax: Optional[float],
) -> List[AircraftRecord]:
    params = {}
    if all(v is not None for v in (lamin, lomin, lamax, lomax)):
        params = {"lamin": lamin, "lomin": lomin, "lamax": lamax, "lomax": lomax}

    url = "https://opensky-network.org/api/states/all"
    if not is_allowed_host(url):
        raise ValueError("Host not allowed")

    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        raw_states = data.get("states") or []

        records: List[AircraftRecord] = []
        for s in raw_states[:500]:  # Limit payload to top 500 active tracks
            if s[5] is None or s[6] is None:
                continue
            records.append(
                AircraftRecord(
                    icao24=str(s[0]).strip().lower(),
                    callsign=str(s[1]).strip() if s[1] else None,
                    origin_country=str(s[2]).strip() if s[2] else None,
                    longitude=float(s[5]),
                    latitude=float(s[6]),
                    baro_altitude=float(s[7]) if s[7] is not None else None,
                    on_ground=bool(s[8]),
                    velocity=float(s[9]) if s[9] is not None else None,
                    true_track=float(s[10]) if s[10] is not None else None,
                    vertical_rate=float(s[11]) if s[11] is not None else None,
                    category="civilian",
                )
            )
        return records


async def fetch_adsb_lol_point(lat: float, lon: float, radius: int = 250) -> List[AircraftRecord]:
    url = f"https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/{radius}"
    if not is_allowed_host(url):
        raise ValueError("Host not allowed")

    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
        ac_list = data.get("ac") or []

        records: List[AircraftRecord] = []
        for ac in ac_list[:300]:
            lat_val = ac.get("lat")
            lon_val = ac.get("lon")
            if lat_val is None or lon_val is None:
                continue
            records.append(
                AircraftRecord(
                    icao24=str(ac.get("hex", "")).strip().lower(),
                    callsign=str(ac.get("flight", "")).strip() or None,
                    origin_country=str(ac.get("dbFlags", "")) or None,
                    longitude=float(lon_val),
                    latitude=float(lat_val),
                    baro_altitude=float(ac.get("alt_baro")) if ac.get("alt_baro") is not None and isinstance(ac.get("alt_baro"), (int, float)) else None,
                    on_ground=ac.get("alt_baro") == "ground",
                    velocity=float(ac.get("gs")) if ac.get("gs") is not None else None,
                    true_track=float(ac.get("track")) if ac.get("track") is not None else None,
                    vertical_rate=float(ac.get("baro_rate")) if ac.get("baro_rate") is not None else None,
                    category="military" if ac.get("mil") else "civilian",
                )
            )
        return records


@router.get("/aircraft", response_model=AircraftResponse)
async def get_live_aircraft(
    lamin: Optional[float] = Query(None),
    lomin: Optional[float] = Query(None),
    lamax: Optional[float] = Query(None),
    lomax: Optional[float] = Query(None),
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    radius: Optional[int] = Query(250),
) -> AircraftResponse:
    """Fetch live aircraft states with automatic failover between OpenSky and ADSB.lol."""
    cache_key = f"aircraft:{lamin}:{lomin}:{lamax}:{lomax}:{lat}:{lon}:{radius}"

    async def _fetch() -> Dict[str, Any]:
        # 1. Try OpenSky first
        try:
            records = await fetch_opensky(lamin, lomin, lamax, lomax)
            if records:
                return {
                    "aircraft": [r.model_dump() for r in records],
                    "source": "opensky",
                    "count": len(records),
                    "timestamp": asyncio.get_event_loop().time(),
                }
        except Exception as e:
            logger.warning("opensky_fetch_failed_attempting_failover", error=str(e))

        # 2. Failover to adsb.lol
        try:
            target_lat = lat if lat is not None else ((lamin + lamax) / 2.0 if lamin is not None and lamax is not None else 32.0)
            target_lon = lon if lon is not None else ((lomin + lomax) / 2.0 if lomin is not None and lomax is not None else 35.0)
            records = await fetch_adsb_lol_point(target_lat, target_lon, radius or 250)
            if records:
                return {
                    "aircraft": [r.model_dump() for r in records],
                    "source": "adsb.lol",
                    "count": len(records),
                    "timestamp": asyncio.get_event_loop().time(),
                }
        except Exception as e:
            logger.warning("adsb_lol_failover_failed", error=str(e))

        # 3. Fallback sample data if both are unreachable
        return {
            "aircraft": [r.model_dump() for r in SAMPLE_FALLBACK_AIRCRAFT],
            "source": "fallback_sim",
            "count": len(SAMPLE_FALLBACK_AIRCRAFT),
            "timestamp": asyncio.get_event_loop().time(),
        }

    data = await singleflight.execute(cache_key, _fetch, ttl_seconds=15.0, allow_stale_on_error=True, timeout_seconds=45.0)
    return AircraftResponse(**data)


@router.get("/aircraft/enrich/{hex}")
async def enrich_aircraft(hex: str) -> Dict[str, Any]:
    """Enrich aircraft metadata (type, airline, manufacturer) via adsbdb.com."""
    hex_clean = hex.strip().lower()
    url = f"https://api.adsbdb.com/v0/aircraft/{hex_clean}"
    cache_key = f"enrich:{hex_clean}"

    async def _fetch() -> Dict[str, Any]:
        if not is_allowed_host(url):
            raise HTTPException(status_code=400, detail="Disallowed host")
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(url)
            if resp.status_code == 404:
                return {"hex": hex_clean, "found": False}
            resp.raise_for_status()
            data = resp.json()
            return {"hex": hex_clean, "found": True, "details": data.get("response", {})}

    try:
        return await singleflight.execute(cache_key, _fetch, ttl_seconds=86400.0, allow_stale_on_error=True)
    except Exception as e:
        logger.warning("aircraft_enrichment_failed", hex=hex_clean, error=str(e))
        return {"hex": hex_clean, "found": False, "error": str(e)}


@router.get("/military")
async def get_military_tracks() -> Dict[str, Any]:
    """Ingest live military aircraft tracks globally via adsb.lol."""
    url = "https://api.adsb.lol/v2/mil"
    cache_key = "aircraft:military_global"

    async def _fetch() -> Dict[str, Any]:
        if not is_allowed_host(url):
            raise HTTPException(status_code=400, detail="Disallowed host")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            ac_list = data.get("ac") or []
            normalized = []
            for ac in ac_list[:500]:
                if ac.get("lat") is None or ac.get("lon") is None:
                    continue
                normalized.append({
                    "icao24": str(ac.get("hex", "")).strip().lower(),
                    "callsign": str(ac.get("flight", "")).strip() or None,
                    "type": ac.get("t"),
                    "latitude": float(ac.get("lat")),
                    "longitude": float(ac.get("lon")),
                    "altitude": float(ac.get("alt_baro")) if isinstance(ac.get("alt_baro"), (int, float)) else None,
                    "velocity": float(ac.get("gs")) if ac.get("gs") is not None else None,
                    "heading": float(ac.get("track")) if ac.get("track") is not None else None,
                    "squawk": ac.get("squawk"),
                    "category": "military",
                })
            return {"count": len(normalized), "tracks": normalized, "source": "adsb.lol"}

    try:
        return await singleflight.execute(cache_key, _fetch, ttl_seconds=30.0, allow_stale_on_error=True)
    except Exception as e:
        logger.warning("military_feed_failed", error=str(e))
        # Provide fallback curated military tracks (e.g. Black Sea / Mediterranean reconnaissance)
        fallback = [
            {
                "icao24": "ae5881",
                "callsign": "FORTE10",
                "type": "RQ4B",
                "latitude": 34.85,
                "longitude": 31.42,
                "altitude": 16200,
                "velocity": 180.2,
                "heading": 85.0,
                "category": "military",
            },
            {
                "icao24": "ae01ce",
                "callsign": "JAKE11",
                "type": "RC135",
                "latitude": 54.55,
                "longitude": 19.82,
                "altitude": 10500,
                "velocity": 230.0,
                "heading": 190.0,
                "category": "military",
            }
        ]
        return {"count": len(fallback), "tracks": fallback, "source": "fallback_sim"}
