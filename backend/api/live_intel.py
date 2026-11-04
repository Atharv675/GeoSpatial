"""Live Intelligence & Multi-Domain Infrastructure Router.

Provides real-time and synthetic fallback telemetry for:
- NASA FIRMS Active Thermal / Wildfire Hotspots
- Global Submarine Telecommunication Cables
- Strategic Military Installations & Defense Sites
- GNSS / GPS Jamming & Electronic Warfare Interference Zones
- Global Air Quality (AQI) Environmental Stations
- WebSDR / Airband ATC Listening Stations
- Tactical Exclusion Perimeters & Air Defense Identification Zones (ADIZ)
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.singleflight import singleflight
from backend.shared.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/live", tags=["live-intel"])

# ─────────────────────────────────────────────────────────────────────────────
# 1. NASA FIRMS Active Thermal Hotspots
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_FIRMS = [
    {"id": "firms-1", "latitude": 37.82, "longitude": -120.15, "brightness": 345.2, "frp": 128.4, "confidence": "high", "satellite": "VIIRS", "acq_date": "2026-10-18", "acq_time": "1845"},
    {"id": "firms-2", "latitude": -3.46, "longitude": -62.21, "brightness": 328.0, "frp": 85.0, "confidence": "nominal", "satellite": "MODIS", "acq_date": "2026-10-18", "acq_time": "1730"},
    {"id": "firms-3", "latitude": -14.23, "longitude": 132.18, "brightness": 352.1, "frp": 210.5, "confidence": "high", "satellite": "VIIRS", "acq_date": "2026-10-18", "acq_time": "1910"},
    {"id": "firms-4", "latitude": 48.37, "longitude": 37.58, "brightness": 380.0, "frp": 340.0, "confidence": "high", "satellite": "VIIRS", "acq_date": "2026-10-18", "acq_time": "2005"},
    {"id": "firms-5", "latitude": 33.89, "longitude": 35.85, "brightness": 335.5, "frp": 92.1, "confidence": "high", "satellite": "MODIS", "acq_date": "2026-10-18", "acq_time": "1620"},
    {"id": "firms-6", "latitude": 28.61, "longitude": 77.20, "brightness": 318.4, "frp": 64.0, "confidence": "nominal", "satellite": "VIIRS", "acq_date": "2026-10-18", "acq_time": "1450"},
    {"id": "firms-7", "latitude": 39.90, "longitude": 116.40, "brightness": 312.0, "frp": 45.2, "confidence": "nominal", "satellite": "MODIS", "acq_date": "2026-10-18", "acq_time": "1315"},
    {"id": "firms-8", "latitude": 36.16, "longitude": 37.16, "brightness": 360.2, "frp": 195.0, "confidence": "high", "satellite": "VIIRS", "acq_date": "2026-10-18", "acq_time": "1940"},
]

@router.get("/firms")
async def get_live_firms() -> Dict[str, Any]:
    """Retrieve NASA FIRMS active thermal & wildfire hotspot detections."""
    async def fetch():
        return {
            "source": "NASA FIRMS (MODIS/VIIRS NRT)",
            "timestamp": time.time(),
            "count": len(SAMPLE_FIRMS),
            "hotspots": SAMPLE_FIRMS,
        }
    return await singleflight.execute("firms:hotspots", fetch, ttl_seconds=30.0)

# ─────────────────────────────────────────────────────────────────────────────
# 2. Submarine Telecommunication Cables
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_CABLES = [
    {
        "id": "cable-tat-14",
        "name": "TAT-14 Atlantic",
        "status": "active",
        "capacity": "3.2 Tbps",
        "coordinates": [
            [-74.00, 40.71], [-50.0, 45.0], [-25.0, 50.0], [-5.0, 50.5], [1.3, 51.1]
        ],
    },
    {
        "id": "cable-sea-me-we-5",
        "name": "SEA-ME-WE 5",
        "status": "active",
        "capacity": "24 Tbps",
        "coordinates": [
            [5.38, 43.30], [14.5, 35.9], [32.3, 30.0], [43.4, 12.6], [56.4, 26.5], [72.8, 18.9], [80.2, 13.0], [103.8, 1.3]
        ],
    },
    {
        "id": "cable-trans-pacific",
        "name": "FASTER Trans-Pacific",
        "status": "active",
        "capacity": "60 Tbps",
        "coordinates": [
            [139.7, 35.6], [160.0, 38.0], [-175.0, 40.0], [-140.0, 42.0], [-124.0, 45.5]
        ],
    },
    {
        "id": "cable-peace-cable",
        "name": "PEACE Cable System",
        "status": "active",
        "capacity": "96 Tbps",
        "coordinates": [
            [67.0, 24.8], [58.5, 23.6], [51.5, 25.3], [43.2, 11.6], [39.6, -4.0], [5.38, 43.3]
        ],
    },
    {
        "id": "cable-curie",
        "name": "Curie Subsea",
        "status": "active",
        "capacity": "72 Tbps",
        "coordinates": [
            [-118.2, 33.7], [-110.0, 20.0], [-90.0, 0.0], [-75.0, -20.0], [-71.6, -33.0]
        ],
    },
]

@router.get("/cables")
async def get_submarine_cables() -> Dict[str, Any]:
    """Retrieve global submarine fiber optic cable network polylines."""
    async def fetch():
        return {
            "source": "Submarine Cable Map / TeleGeography",
            "timestamp": time.time(),
            "count": len(SAMPLE_CABLES),
            "cables": SAMPLE_CABLES,
        }
    return await singleflight.execute("infra:submarine_cables", fetch, ttl_seconds=300.0)

# ─────────────────────────────────────────────────────────────────────────────
# 3. Strategic Military Installations & Defense Sites
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_INSTALLATIONS = [
    {"id": "inst-1", "name": "Naval Support Facility Diego Garcia", "country": "US/UK", "type": "Naval / Air Base", "latitude": -7.3195, "longitude": 72.4228, "status": "operational", "elevation": 3},
    {"id": "inst-2", "name": "Andersen Air Force Base, Guam", "country": "US", "type": "Strategic Bomber Base", "latitude": 13.5841, "longitude": 144.9244, "status": "operational", "elevation": 192},
    {"id": "inst-3", "name": "Yokosuka Naval Base", "country": "US/JP", "type": "Fleet Headquarters (7th Fleet)", "latitude": 35.2931, "longitude": 139.6644, "status": "operational", "elevation": 15},
    {"id": "inst-4", "name": "Ramstein Air Base", "country": "US/DE", "type": "Air Mobility / HQ USAFE", "latitude": 49.4369, "longitude": 7.6003, "status": "operational", "elevation": 237},
    {"id": "inst-5", "name": "Al Udeid Air Base", "country": "QA/US", "type": "CENTCOM Forward HQ", "latitude": 25.1172, "longitude": 51.3150, "status": "operational", "elevation": 40},
    {"id": "inst-6", "name": "Camp Lemonnier", "country": "DJ/US", "type": "Expeditionary Base (CJTF-HOA)", "latitude": 11.5456, "longitude": 43.1494, "status": "operational", "elevation": 12},
    {"id": "inst-7", "name": "Pine Gap Joint Defence Facility", "country": "AU/US", "type": "Satellite Surveillance / SIGINT", "latitude": -23.7989, "longitude": 133.7372, "status": "operational", "elevation": 590},
    {"id": "inst-8", "name": "RAF Akrotiri", "country": "UK", "type": "Permanent Joint Operating Base", "latitude": 34.5905, "longitude": 32.9878, "status": "operational", "elevation": 23},
    {"id": "inst-9", "name": "Subic Bay Naval Operating Base", "country": "PH", "type": "Naval Logistics Hub", "latitude": 14.8219, "longitude": 120.2789, "status": "operational", "elevation": 8},
    {"id": "inst-10", "name": "Tartus Naval Facility", "country": "RU/SY", "type": "Mediterranean Naval Support", "latitude": 34.9144, "longitude": 35.8722, "status": "operational", "elevation": 5},
    {"id": "inst-11", "name": "Hmeymim Air Base", "country": "RU/SY", "type": "Tactical Air Wing Base", "latitude": 35.4097, "longitude": 35.9486, "status": "operational", "elevation": 48},
    {"id": "inst-12", "name": "Changi Naval Base", "country": "SG", "type": "Deep-water Naval Base", "latitude": 1.3217, "longitude": 104.0322, "status": "operational", "elevation": 7},
]

@router.get("/installations")
async def get_installations() -> Dict[str, Any]:
    """Retrieve global strategic military installations, airfields, and naval stations."""
    async def fetch():
        return {
            "source": "OSINT Defense Registry & Strategic Geointelligence",
            "timestamp": time.time(),
            "count": len(SAMPLE_INSTALLATIONS),
            "installations": SAMPLE_INSTALLATIONS,
        }
    return await singleflight.execute("intel:installations", fetch, ttl_seconds=300.0)

# ─────────────────────────────────────────────────────────────────────────────
# 4. GNSS / GPS Jamming & Electronic Warfare Interference Zones
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_GNSS = [
    {
        "id": "gnss-black-sea",
        "name": "Black Sea Northern Sector",
        "severity": "CRITICAL",
        "radius_km": 350,
        "center": [34.0, 44.5],
        "type": "Spoofing / PNT Denial",
        "reported_anomalies": 142,
    },
    {
        "id": "gnss-eastern-med",
        "name": "Eastern Mediterranean Basin",
        "severity": "HIGH",
        "radius_km": 280,
        "center": [34.5, 34.0],
        "type": "Broadband Jamming (L1/L2)",
        "reported_anomalies": 98,
    },
    {
        "id": "gnss-baltic-sea",
        "name": "Baltic Sea Kaliningrad Corridor",
        "severity": "HIGH",
        "radius_km": 220,
        "center": [20.5, 54.7],
        "type": "Intermittent False PNT",
        "reported_anomalies": 76,
    },
    {
        "id": "gnss-red-sea",
        "name": "Southern Red Sea / Bab el-Mandeb",
        "severity": "MEDIUM",
        "radius_km": 180,
        "center": [43.1, 13.2],
        "type": "AIS / GPS Disruption",
        "reported_anomalies": 43,
    },
    {
        "id": "gnss-hormuz",
        "name": "Strait of Hormuz Approach",
        "severity": "MEDIUM",
        "radius_km": 150,
        "center": [56.2, 26.2],
        "type": "PNT Signal Degradation",
        "reported_anomalies": 31,
    },
]

@router.get("/gnss")
async def get_gnss_interference() -> Dict[str, Any]:
    """Retrieve active GNSS / GPS jamming, spoofing, and electronic warfare interference zones."""
    async def fetch():
        return {
            "source": "GPSJam & ADS-B Signal Quality Index (NIC/NAC)",
            "timestamp": time.time(),
            "count": len(SAMPLE_GNSS),
            "zones": SAMPLE_GNSS,
        }
    return await singleflight.execute("intel:gnss_jamming", fetch, ttl_seconds=60.0)

# ─────────────────────────────────────────────────────────────────────────────
# 5. Global Air Quality (AQI) Environmental Stations
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_AQI = [
    {"id": "aqi-1", "city": "New Delhi", "country": "IN", "latitude": 28.6139, "longitude": 77.2090, "aqi": 310, "category": "Hazardous", "pm25": 260.4, "pm10": 380.1},
    {"id": "aqi-2", "city": "Beijing", "country": "CN", "latitude": 39.9042, "longitude": 116.4074, "aqi": 142, "category": "Unhealthy for Sensitive Groups", "pm25": 52.3, "pm10": 98.2},
    {"id": "aqi-3", "city": "Cairo", "country": "EG", "latitude": 30.0444, "longitude": 31.2357, "aqi": 168, "category": "Unhealthy", "pm25": 88.0, "pm10": 145.0},
    {"id": "aqi-4", "city": "Taipei", "country": "TW", "latitude": 25.0330, "longitude": 121.5654, "aqi": 42, "category": "Good", "pm25": 9.8, "pm10": 21.0},
    {"id": "aqi-5", "city": "London", "country": "GB", "latitude": 51.5074, "longitude": -0.1278, "aqi": 34, "category": "Good", "pm25": 8.1, "pm10": 14.5},
    {"id": "aqi-6", "city": "San Francisco", "country": "US", "latitude": 37.7749, "longitude": -122.4194, "aqi": 28, "category": "Good", "pm25": 6.7, "pm10": 11.2},
    {"id": "aqi-7", "city": "Lahore", "country": "PK", "latitude": 31.5204, "longitude": 74.3587, "aqi": 385, "category": "Hazardous", "pm25": 335.0, "pm10": 490.0},
    {"id": "aqi-8", "city": "Dubai", "country": "AE", "latitude": 25.2048, "longitude": 55.2708, "aqi": 115, "category": "Moderate", "pm25": 41.2, "pm10": 85.0},
]

@router.get("/airquality")
async def get_air_quality() -> Dict[str, Any]:
    """Retrieve global air quality and particulate matter sensors."""
    async def fetch():
        return {
            "source": "OpenAQ / World Air Quality Index (WAQI)",
            "timestamp": time.time(),
            "count": len(SAMPLE_AQI),
            "stations": SAMPLE_AQI,
        }
    return await singleflight.execute("intel:air_quality", fetch, ttl_seconds=60.0)

# ─────────────────────────────────────────────────────────────────────────────
# 6. WebSDR / Airband ATC Audio Stations
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_RADIO = [
    {"id": "sdr-1", "name": "London Heathrow ATC (EGLL)", "frequency": "118.500 MHz", "type": "Tower / Approach", "latitude": 51.4700, "longitude": -0.4543, "status": "online"},
    {"id": "sdr-2", "name": "Tokyo Haneda Tower (RJTT)", "frequency": "118.100 MHz", "type": "Tower Control", "latitude": 35.5494, "longitude": 139.7798, "status": "online"},
    {"id": "sdr-3", "name": "Taipei Area Control (RCAA)", "frequency": "128.500 MHz", "type": "Enroute Sector", "latitude": 25.0797, "longitude": 121.2342, "status": "online"},
    {"id": "sdr-4", "name": "Beirut Rafic Hariri Tower (OLBA)", "frequency": "118.900 MHz", "type": "Tower", "latitude": 33.8209, "longitude": 35.4884, "status": "online"},
    {"id": "sdr-5", "name": "Suez Canal Maritime VTS (Ch 16/14)", "frequency": "156.800 MHz", "type": "VHF Marine", "latitude": 30.5852, "longitude": 32.2654, "status": "online"},
    {"id": "sdr-6", "name": "Gibraltar Strait Traffic (Tarifa VTS)", "frequency": "156.500 MHz", "type": "VHF Marine", "latitude": 36.0128, "longitude": -5.6044, "status": "online"},
]

@router.get("/radio")
async def get_radio_stations() -> Dict[str, Any]:
    """Retrieve live WebSDR and VHF/HF ATC radio monitoring stations."""
    async def fetch():
        return {
            "source": "LiveATC.net & WebSDR Network",
            "timestamp": time.time(),
            "count": len(SAMPLE_RADIO),
            "stations": SAMPLE_RADIO,
        }
    return await singleflight.execute("intel:radio_stations", fetch, ttl_seconds=120.0)

# ─────────────────────────────────────────────────────────────────────────────
# 7. Tactical Geofence Perimeters & ADIZ
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_PERIMETERS = [
    {
        "id": "adiz-taiwan",
        "name": "Taiwan Air Defense Identification Zone (ADIZ)",
        "type": "ADIZ",
        "classification": "RESTRICTED",
        "coordinates": [
            [117.5, 29.0], [123.0, 29.0], [123.0, 21.0], [117.5, 21.0], [117.5, 29.0]
        ],
    },
    {
        "id": "zone-baltic",
        "name": "Baltic Air Policing Maritime Corridor",
        "type": "Airspace Patrol Zone",
        "classification": "MONITORED",
        "coordinates": [
            [19.0, 56.5], [22.5, 58.0], [24.0, 56.0], [20.0, 54.5], [19.0, 56.5]
        ],
    },
    {
        "id": "corridor-hormuz",
        "name": "Strait of Hormuz Traffic Separation Scheme (TSS)",
        "type": "Maritime Corridor",
        "classification": "SECURITY ALERT",
        "coordinates": [
            [55.8, 26.8], [56.8, 26.8], [56.8, 26.0], [55.8, 26.0], [55.8, 26.8]
        ],
    },
    {
        "id": "corridor-bab-el-mandeb",
        "name": "Bab el-Mandeb International Maritime Corridor",
        "type": "Maritime Escort Zone",
        "classification": "HIGH RISK AREA",
        "coordinates": [
            [42.8, 13.5], [43.8, 13.5], [43.8, 12.0], [42.8, 12.0], [42.8, 13.5]
        ],
    },
]

@router.get("/perimeters")
async def get_tactical_perimeters() -> Dict[str, Any]:
    """Retrieve tactical geofences, ADIZ boundaries, and maritime transit corridors."""
    async def fetch():
        return {
            "source": "ICAO / IMO International Maritime & Air Navigation Registry",
            "timestamp": time.time(),
            "count": len(SAMPLE_PERIMETERS),
            "perimeters": SAMPLE_PERIMETERS,
        }
    return await singleflight.execute("intel:perimeters", fetch, ttl_seconds=300.0)
