"""Live CCTV & Road-Weather Camera Telemetry Router.

Aggregates public traffic cameras from municipal and national agencies
and securely relays live camera frame snapshots with SSRF guardrails.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query, Response

from backend.services.singleflight import is_allowed_host, safe_http_get, singleflight
from backend.shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/live", tags=["live-cctv"])

# Curated catalog of high-reliability public cameras across agencies
PUBLIC_CCTV_CATALOG = [
    {
        "id": "tfl-jamcam-001",
        "name": "TfL JamCam: Trafalgar Square",
        "agency": "Transport for London (UK)",
        "latitude": 51.5080,
        "longitude": -0.1281,
        "imageUrl": "https://s3-eu-west-1.amazonaws.com/jamcams.tfl.gov.uk/00001.07358.jpg",
        "status": "active",
        "refreshSeconds": 10,
    },
    {
        "id": "tfl-jamcam-002",
        "name": "TfL JamCam: Westminster Bridge",
        "agency": "Transport for London (UK)",
        "latitude": 51.5010,
        "longitude": -0.1246,
        "imageUrl": "https://s3-eu-west-1.amazonaws.com/jamcams.tfl.gov.uk/00001.07380.jpg",
        "status": "active",
        "refreshSeconds": 10,
    },
    {
        "id": "caltrans-d4-baybridge",
        "name": "Caltrans D4: SF-Oakland Bay Bridge East Span",
        "agency": "Caltrans (California, USA)",
        "latitude": 37.8188,
        "longitude": -122.3550,
        "imageUrl": "https://cwwp2.dot.ca.gov/data/d4/cctv/image/i80atbaybridgeyerbabuena/i80atbaybridgeyerbabuena.jpg",
        "status": "active",
        "refreshSeconds": 30,
    },
    {
        "id": "txdot-austin-i35",
        "name": "TxDOT Austin: IH-35 @ 6th Street",
        "agency": "Texas DOT (USA)",
        "latitude": 30.2672,
        "longitude": -97.7331,
        "imageUrl": "https://its.txdot.gov/its/cctv/austin/0035-02-04.jpg",
        "status": "active",
        "refreshSeconds": 20,
    },
    {
        "id": "fintraffic-helsinki",
        "name": "Fintraffic: E12 Vantaa Airport Access",
        "agency": "Fintraffic (Finland)",
        "latitude": 60.3172,
        "longitude": 24.9633,
        "imageUrl": "https://weathercam.digitraffic.fi/C0150101.jpg",
        "status": "active",
        "refreshSeconds": 60,
    },
    {
        "id": "vegvesen-oslo",
        "name": "Statens Vegvesen: E6 Oslo Ring",
        "agency": "Statens Vegvesen (Norway)",
        "latitude": 59.9139,
        "longitude": 10.7522,
        "imageUrl": "https://webkamera.vegvesen.no/kamera?id=101001",
        "status": "active",
        "refreshSeconds": 60,
    },
]


@router.get("/cctv/cameras")
async def get_cctv_cameras() -> Dict[str, Any]:
    """Return aggregated normalized catalog of public traffic & surveillance cameras."""
    return {
        "count": len(PUBLIC_CCTV_CATALOG),
        "cameras": PUBLIC_CCTV_CATALOG,
        "agencies": [
            "Transport for London",
            "Caltrans",
            "Texas DOT",
            "Fintraffic",
            "Statens Vegvesen",
            "Ontario 511",
            "DriveBC",
        ],
    }


@router.get("/cctv/frame")
async def get_cctv_frame(url: str = Query(..., description="Target camera frame URL")) -> Response:
    """Securely proxy/relay a live camera snapshot with strict host validation."""
    if not is_allowed_host(url):
        raise HTTPException(
            status_code=403,
            detail="Forbidden: camera host is not on the GeoSentinel proxy allowlist",
        )

    cache_key = f"cctv_frame:{url}"

    async def _fetch() -> bytes:
        return await safe_http_get(url, timeout=6.0, as_json=False)

    try:
        image_bytes = await singleflight.execute(
            cache_key,
            _fetch,
            ttl_seconds=10.0,
            allow_stale_on_error=True,
            timeout_seconds=8.0,
        )
        return Response(content=image_bytes, media_type="image/jpeg")
    except Exception as e:
        logger.warning("cctv_frame_proxy_failed", url=url, error=str(e))
        # Return a lightweight 1x1 transparent SVG / placeholder
        placeholder_svg = (
            b'<svg xmlns="http://www.w3.org/2000/svg" width="320" height="240" viewBox="0 0 320 240">'
            b'<rect width="320" height="240" fill="#0d1524"/>'
            b'<text x="50%" y="50%" fill="#00e5ff" font-family="monospace" font-size="12" '
            b'text-anchor="middle" dominant-baseline="middle">FEED TEMPORARILY OFFLINE</text>'
            b'</svg>'
        )
        return Response(content=placeholder_svg, media_type="image/svg+xml")
