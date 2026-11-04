"""Aggregate API routers."""

from fastapi import APIRouter

from backend.api import (
    analysis,
    aois,
    explainability,
    health,
    ingestion,
    live_aircraft,
    live_cctv,
    live_earthquakes,
    live_intel,
    live_satellites,
    live_transit,
    live_vessels,
    live_weather,
    osint,
    preprocessing,
    registry,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(registry.router)
api_router.include_router(aois.router)
api_router.include_router(ingestion.router)
api_router.include_router(preprocessing.router)
api_router.include_router(analysis.router)
api_router.include_router(osint.router)
api_router.include_router(explainability.router)

# Phase 1: Real-time Multi-Domain Telemetry Routers
api_router.include_router(live_aircraft.router)
api_router.include_router(live_vessels.router)
api_router.include_router(live_satellites.router)
api_router.include_router(live_weather.router)
api_router.include_router(live_cctv.router)
api_router.include_router(live_transit.router)
api_router.include_router(live_earthquakes.router)
api_router.include_router(live_intel.router)
