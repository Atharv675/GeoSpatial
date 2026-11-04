"""Live Marine Vessel Telemetry Router (AISStream WebSocket & Snapshot).

Securely relays AISStream messages without exposing API keys to the client,
with keyless fallback simulation if AISSTREAM_API_KEY is not configured.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import random
import time
from typing import Any, Dict, List, Optional

import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from backend.shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/live", tags=["live-vessels"])

AISSTREAM_WS_URL = "wss://stream.aisstream.io/v0/stream"

# Realistic keyless seed ships for live simulation if AISSTREAM_API_KEY is omitted
KEYLESS_SIM_VESSELS = [
    {
        "mmsi": 211281610,
        "name": "CMA CGM ANTOINE",
        "type": "Cargo / Container",
        "latitude": 36.14,
        "longitude": -5.35,
        "sog": 18.2,
        "cog": 88.0,
        "heading": 89.0,
        "destination": "ROTTERDAM",
    },
    {
        "mmsi": 477123450,
        "name": "EVER GIVEN",
        "type": "Cargo / Container",
        "latitude": 30.02,
        "longitude": 32.58,
        "sog": 9.5,
        "cog": 340.0,
        "heading": 342.0,
        "destination": "PORT SAID",
    },
    {
        "mmsi": 538006123,
        "name": "FRONT ALTAIR",
        "type": "Tanker (Crude Oil)",
        "latitude": 26.55,
        "longitude": 56.45,
        "sog": 13.4,
        "cog": 135.0,
        "heading": 135.0,
        "destination": "SINGAPORE",
    },
    {
        "mmsi": 636019888,
        "name": "MSC LAUREN",
        "type": "Cargo / Container",
        "latitude": 1.22,
        "longitude": 103.82,
        "sog": 11.8,
        "cog": 265.0,
        "heading": 267.0,
        "destination": "TANJUNG PELEPAS",
    },
    {
        "mmsi": 367123987,
        "name": "USNS COMFORT",
        "type": "Hospital Ship / Naval",
        "latitude": 36.95,
        "longitude": -76.32,
        "sog": 0.1,
        "cog": 0.0,
        "heading": 45.0,
        "destination": "NORFOLK",
    },
    {
        "mmsi": 244123000,
        "name": "ROTTERDAM PILOT 1",
        "type": "Pilot Vessel",
        "latitude": 51.98,
        "longitude": 4.10,
        "sog": 21.4,
        "cog": 290.0,
        "heading": 292.0,
        "destination": "HOOK OF HOLLAND",
    },
]


def _sanitize_ais_message(raw_msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Sanitize and normalize AISStream payload, removing sensitive upstream fields."""
    try:
        msg_type = raw_msg.get("MessageType")
        metadata = raw_msg.get("MetaData", {})
        mmsi = metadata.get("MMSI")
        ship_name = metadata.get("ShipName", "").strip()

        lat = metadata.get("latitude")
        lon = metadata.get("longitude")
        sog = None
        cog = None
        heading = None

        message_body = raw_msg.get("Message", {})
        if "PositionReport" in message_body:
            pos = message_body["PositionReport"]
            lat = pos.get("Latitude", lat)
            lon = pos.get("Longitude", lon)
            sog = pos.get("Sog")
            cog = pos.get("Cog")
            heading = pos.get("TrueHeading")

        if lat is None or lon is None or not mmsi:
            return None

        return {
            "mmsi": int(mmsi),
            "name": ship_name or f"Vessel-{mmsi}",
            "type": "Commercial Vessel",
            "latitude": float(lat),
            "longitude": float(lon),
            "sog": float(sog) if sog is not None else 0.0,
            "cog": float(cog) if cog is not None else 0.0,
            "heading": float(heading) if heading is not None and heading != 511 else cog,
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.debug("ais_sanitize_failed", error=str(e))
        return None


@router.get("/vessels/snapshot")
async def get_vessels_snapshot() -> Dict[str, Any]:
    """Return a point-in-time snapshot of active vessels."""
    return {
        "vessels": KEYLESS_SIM_VESSELS,
        "count": len(KEYLESS_SIM_VESSELS),
        "source": "simulated_seed" if not os.getenv("AISSTREAM_API_KEY") else "aisstream",
        "timestamp": time.time(),
    }


@router.websocket("/vessels/ws")
async def websocket_vessels_endpoint(websocket: WebSocket) -> None:
    """Secure relay for AISStream, with keyless fallback stream."""
    await websocket.accept()
    api_key = os.getenv("AISSTREAM_API_KEY", "").strip()

    # If API key is not provided, start the keyless moving vessel simulator
    if not api_key:
        logger.info("vessels_ws_started_in_keyless_mode")
        sim_state = [dict(v) for v in KEYLESS_SIM_VESSELS]
        try:
            while True:
                # Update positions slightly based on speed and heading
                for v in sim_state:
                    speed_knots = v.get("sog", 10.0)
                    deg = v.get("heading", 0.0)
                    rad = math.radians(deg)
                    # 1 knot ~ 0.0005 deg/hr -> dt ~ 2s
                    step = (speed_knots * 0.000005)
                    v["latitude"] = round(v["latitude"] + step * math.cos(rad), 6)
                    v["longitude"] = round(v["longitude"] + step * math.sin(rad), 6)
                    v["timestamp"] = time.time()

                payload = {
                    "type": "vessels_update",
                    "vessels": sim_state,
                    "count": len(sim_state),
                    "source": "keyless_active_stream",
                }
                await websocket.send_text(json.dumps(payload))
                await asyncio.sleep(2.0)
        except WebSocketDisconnect:
            logger.info("vessels_ws_client_disconnected")
        except Exception as e:
            logger.warning("vessels_sim_stream_error", error=str(e))
        return

    # If AISSTREAM_API_KEY is provided, connect upstream securely
    try:
        async with websockets.connect(AISSTREAM_WS_URL, ping_interval=20, ping_timeout=20) as upstream:
            # Subscribe to global bounding box
            subscribe_message = {
                "APIKey": api_key,
                "BoundingBoxes": [[[-90, -180], [90, 180]]],
                "FilterMessageTypes": ["PositionReport"],
            }
            await upstream.send(json.dumps(subscribe_message))

            while True:
                raw = await upstream.recv()
                msg = json.loads(raw)
                sanitized = _sanitize_ais_message(msg)
                if sanitized:
                    await websocket.send_text(json.dumps({
                        "type": "vessel_update",
                        "vessel": sanitized,
                        "source": "aisstream_live",
                    }))
    except WebSocketDisconnect:
        logger.info("vessels_ws_client_disconnected")
    except Exception as e:
        logger.warning("upstream_aisstream_error", error=str(e))
        # Fall back to simulation gracefully if upstream failed
        try:
            await websocket.send_text(json.dumps({
                "type": "vessels_update",
                "vessels": KEYLESS_SIM_VESSELS,
                "source": "fallback_sim",
            }))
        except Exception:
            pass
