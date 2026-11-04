"""Live Meteorological Telemetry Router.

Serves NOAA nowCOAST WMS radar endpoints, NOAA NHC tropical cyclone advisories,
and Open-Meteo tactical weather readouts.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query

from backend.services.singleflight import is_allowed_host, singleflight
from backend.shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/live", tags=["live-weather"])

NOWCOAST_WMS_URL = "https://nowcoast.noaa.gov/geoserver/observations/weather_radar/ows"
NHC_STORMS_URL = "https://www.nhc.noaa.gov/CurrentStorms.json"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


@router.get("/weather/radar-wms")
async def get_radar_wms_config() -> Dict[str, Any]:
    """Return NOAA nowCOAST MRMS Base Reflectivity WMS layer configuration."""
    return {
        "service": "WMS",
        "version": "1.3.0",
        "url": NOWCOAST_WMS_URL,
        "layers": "conus_base_reflectivity_mosaic",
        "format": "image/png",
        "transparent": True,
        "opacity": 0.65,
        "attribution": "NOAA / NWS nowCOAST",
        "crs": "EPSG:3857",
    }


@router.get("/weather/cyclones")
async def get_cyclone_advisories() -> Dict[str, Any]:
    """Ingest NOAA NHC tropical cyclone advisory status, cached for 5 minutes."""
    cache_key = "weather:cyclones"

    async def _fetch() -> Dict[str, Any]:
        if not is_allowed_host(NHC_STORMS_URL):
            raise HTTPException(status_code=400, detail="Disallowed host")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(NHC_STORMS_URL)
            resp.raise_for_status()
            return resp.json()

    try:
        return await singleflight.execute(cache_key, _fetch, ttl_seconds=300.0, allow_stale_on_error=True)
    except Exception as e:
        logger.warning("nhc_cyclones_fetch_failed", error=str(e))
        return {
            "activeStorms": [],
            "source": "fallback",
            "message": "No active tropical storms or upstream unavailable",
        }


@router.get("/weather/local")
async def get_local_weather(
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0),
) -> Dict[str, Any]:
    """Ingest cockpit meteorological readings from Open-Meteo, cached by 0.1° cell."""
    lat_round = round(latitude, 1)
    lon_round = round(longitude, 1)
    cache_key = f"weather:local:{lat_round}:{lon_round}"

    async def _fetch() -> Dict[str, Any]:
        params = {
            "latitude": lat_round,
            "longitude": lon_round,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,cloud_cover,wind_speed_10m,wind_direction_10m,surface_pressure",
            "timezone": "UTC",
        }
        if not is_allowed_host(OPEN_METEO_URL):
            raise HTTPException(status_code=400, detail="Disallowed host")

        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(OPEN_METEO_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            current = data.get("current", {})
            return {
                "latitude": lat_round,
                "longitude": lon_round,
                "elevation": data.get("elevation"),
                "temperature_c": current.get("temperature_2m"),
                "relative_humidity": current.get("relative_humidity_2m"),
                "wind_speed_kmh": current.get("wind_speed_10m"),
                "wind_direction_deg": current.get("wind_direction_10m"),
                "cloud_cover_percent": current.get("cloud_cover"),
                "surface_pressure_hpa": current.get("surface_pressure"),
                "weather_code": current.get("weather_code"),
                "source": "open-meteo",
            }

    try:
        return await singleflight.execute(cache_key, _fetch, ttl_seconds=600.0, allow_stale_on_error=True)
    except Exception as e:
        logger.warning("open_meteo_fetch_failed", error=str(e))
        return {
            "latitude": lat_round,
            "longitude": lon_round,
            "temperature_c": 18.0,
            "relative_humidity": 50,
            "wind_speed_kmh": 12.0,
            "wind_direction_deg": 180,
            "cloud_cover_percent": 20,
            "surface_pressure_hpa": 1013.25,
            "weather_code": 0,
            "source": "fallback_standard_atmosphere",
        }
