"""Live Satellite & Space Launch Telemetry Router.

Ingests active CelesTrak orbital TLE sets and upcoming orbital launches
from Launch Library 2 with singleflight deduplication and caching.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query

from backend.services.singleflight import is_allowed_host, singleflight
from backend.shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/live", tags=["live-satellites"])

CELESTRAK_ACTIVE_TLE_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
LAUNCH_LIBRARY_URL = "https://ll.thespacedevs.com/2.3.0/launches/?limit=20&ordering=net"

# Curated fallback TLEs for key earth-observation & recon satellites
FALLBACK_TLES = [
    {
        "name": "ISS (ZARYA)",
        "line1": "1 25544U 98067A   24290.52857488  .00014285  00000+0  25752-3 0  9997",
        "line2": "2 25544  51.6412 181.7924 0006764  73.2385 286.9744 15.49842145477813",
        "norad_cat_id": 25544,
    },
    {
        "name": "SENTINEL-1A",
        "line1": "1 39634U 14016A   24290.48512140  .00000021  00000+0  16324-4 0  9998",
        "line2": "2 39634  98.1818 342.3129 0001283  94.6128 265.5283 14.59198642560882",
        "norad_cat_id": 39634,
    },
    {
        "name": "SENTINEL-2A",
        "line1": "1 40697U 15028A   24290.49120412  .00000092  00000+0  31482-4 0  9992",
        "line2": "2 40697  98.5702 334.8412 0001157  87.2140 272.9213 14.30820412487403",
        "norad_cat_id": 40697,
    },
    {
        "name": "TERRA (EOS AM-1)",
        "line1": "1 25994U 99068A   24290.43284051  .00000624  00000+0  13572-3 0  9995",
        "line2": "2 25994  98.2045 348.5120 0001391  92.5183 267.6219 14.57112041315801",
        "norad_cat_id": 25994,
    },
    {
        "name": "HUBBLE SPACE TELESCOPE",
        "line1": "1 20580U 90037B   24290.50124810  .00001540  00000+0  68912-4 0  9991",
        "line2": "2 20580  28.4691 210.4281 0002914 314.1205  45.8912 15.09341209865103",
        "norad_cat_id": 20580,
    },
]


def parse_tle_text(tle_text: str, max_records: int = 150) -> List[Dict[str, Any]]:
    lines = [line.strip() for line in tle_text.strip().splitlines() if line.strip()]
    records = []
    i = 0
    while i < len(lines) - 2 and len(records) < max_records:
        name = lines[i]
        l1 = lines[i + 1]
        l2 = lines[i + 2]
        if l1.startswith("1 ") and l2.startswith("2 "):
            try:
                norad = int(l1[2:7].strip())
            except ValueError:
                norad = 0
            records.append({
                "name": name,
                "line1": l1,
                "line2": l2,
                "norad_cat_id": norad,
            })
            i += 3
        else:
            i += 1
    return records


@router.get("/satellites/tle")
async def get_satellites_tle(limit: int = Query(100, ge=1, le=500)) -> Dict[str, Any]:
    """Ingest active orbital TLEs from CelesTrak, cached for 2 hours."""
    cache_key = f"satellites:tle:{limit}"

    async def _fetch() -> Dict[str, Any]:
        if not is_allowed_host(CELESTRAK_ACTIVE_TLE_URL):
            raise HTTPException(status_code=400, detail="Disallowed host")
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get(CELESTRAK_ACTIVE_TLE_URL)
            resp.raise_for_status()
            text = resp.text
            records = parse_tle_text(text, max_records=limit)
            return {
                "count": len(records),
                "satellites": records,
                "source": "celestrak",
            }

    try:
        return await singleflight.execute(cache_key, _fetch, ttl_seconds=7200.0, allow_stale_on_error=True)
    except Exception as e:
        logger.warning("celestrak_fetch_failed_using_fallback", error=str(e))
        return {
            "count": len(FALLBACK_TLES),
            "satellites": FALLBACK_TLES,
            "source": "fallback_seed",
        }


@router.get("/space/launches")
async def get_space_launches() -> Dict[str, Any]:
    """Ingest upcoming rocket launches from Launch Library 2, cached for 15 minutes."""
    cache_key = "space:launches"

    async def _fetch() -> Dict[str, Any]:
        if not is_allowed_host(LAUNCH_LIBRARY_URL):
            raise HTTPException(status_code=400, detail="Disallowed host")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(LAUNCH_LIBRARY_URL)
            resp.raise_for_status()
            data = resp.json()
            raw_results = data.get("results") or []
            normalized = []
            for item in raw_results:
                pad = item.get("pad", {})
                normalized.append({
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "net": item.get("net"),
                    "status": (item.get("status") or {}).get("name"),
                    "provider": (item.get("launch_service_provider") or {}).get("name"),
                    "rocket": (item.get("rocket") or {}).get("configuration", {}).get("full_name"),
                    "pad_name": pad.get("name"),
                    "latitude": float(pad.get("latitude")) if pad.get("latitude") is not None else None,
                    "longitude": float(pad.get("longitude")) if pad.get("longitude") is not None else None,
                    "location_name": (pad.get("location") or {}).get("name"),
                })
            return {"count": len(normalized), "launches": normalized, "source": "launch_library_2"}

    try:
        return await singleflight.execute(cache_key, _fetch, ttl_seconds=900.0, allow_stale_on_error=True)
    except Exception as e:
        logger.warning("launch_library_fetch_failed", error=str(e))
        return {"count": 0, "launches": [], "source": "unavailable", "error": str(e)}
