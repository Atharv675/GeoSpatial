"""Tests for Phase 1 Multi-Source Real-Time Ingestion and Telemetry APIs."""

import pytest
from httpx import AsyncClient

from backend.services.singleflight import is_allowed_host


def test_ssrf_host_allowlist_guard():
    assert is_allowed_host("https://opensky-network.org/api/states/all") is True
    assert is_allowed_host("https://api.adsb.lol/v2/mil") is True
    assert is_allowed_host("https://celestrak.org/NORAD/elements/gp.php") is True
    assert is_allowed_host("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson") is True

    # Blocked hosts / internal loopbacks
    assert is_allowed_host("http://127.0.0.1:8000/admin") is False
    assert is_allowed_host("http://localhost/secret") is False
    assert is_allowed_host("http://169.254.169.254/latest/meta-data/") is False
    assert is_allowed_host("https://evil-attacker.com/malicious.jpg") is False


@pytest.mark.anyio
async def test_live_aircraft_endpoint(client: AsyncClient):
    r = await client.get("/api/live/aircraft")
    assert r.status_code == 200
    data = r.json()
    assert "aircraft" in data
    assert "source" in data
    assert "count" in data
    assert isinstance(data["aircraft"], list)


@pytest.mark.anyio
async def test_live_aircraft_enrich_endpoint(client: AsyncClient):
    r = await client.get("/api/live/aircraft/enrich/ae5881")
    assert r.status_code == 200
    data = r.json()
    assert data["hex"] == "ae5881"


@pytest.mark.anyio
async def test_live_military_tracks(client: AsyncClient):
    r = await client.get("/api/live/military")
    assert r.status_code == 200
    data = r.json()
    assert "tracks" in data
    assert "count" in data


@pytest.mark.anyio
async def test_live_vessels_snapshot(client: AsyncClient):
    r = await client.get("/api/live/vessels/snapshot")
    assert r.status_code == 200
    data = r.json()
    assert "vessels" in data
    assert len(data["vessels"]) > 0
    first = data["vessels"][0]
    assert "mmsi" in first
    assert "latitude" in first
    assert "longitude" in first


@pytest.mark.anyio
async def test_live_satellites_tle(client: AsyncClient):
    r = await client.get("/api/live/satellites/tle?limit=10")
    assert r.status_code == 200
    data = r.json()
    assert "satellites" in data
    assert len(data["satellites"]) > 0
    sat = data["satellites"][0]
    assert "name" in sat
    assert "line1" in sat
    assert "line2" in sat


@pytest.mark.anyio
async def test_live_space_launches(client: AsyncClient):
    r = await client.get("/api/live/space/launches")
    assert r.status_code == 200
    data = r.json()
    assert "launches" in data


@pytest.mark.anyio
async def test_live_weather_radar_wms(client: AsyncClient):
    r = await client.get("/api/live/weather/radar-wms")
    assert r.status_code == 200
    data = r.json()
    assert data["layers"] == "conus_base_reflectivity_mosaic"
    assert "nowcoast.noaa.gov" in data["url"]


@pytest.mark.anyio
async def test_live_weather_cyclones(client: AsyncClient):
    r = await client.get("/api/live/weather/cyclones")
    assert r.status_code == 200


@pytest.mark.anyio
async def test_live_weather_local(client: AsyncClient):
    r = await client.get("/api/live/weather/local?latitude=32.0&longitude=35.0")
    assert r.status_code == 200
    data = r.json()
    assert data["latitude"] == 32.0
    assert data["longitude"] == 35.0
    assert "temperature_c" in data


@pytest.mark.anyio
async def test_live_cctv_catalog_and_security(client: AsyncClient):
    r = await client.get("/api/live/cctv/cameras")
    assert r.status_code == 200
    data = r.json()
    assert "cameras" in data
    assert len(data["cameras"]) > 0

    # SSRF guard test on frame relay
    r_bad = await client.get("/api/live/cctv/frame?url=http://127.0.0.1:8000/secrets")
    assert r_bad.status_code == 403


@pytest.mark.anyio
async def test_live_transit_vehicles(client: AsyncClient):
    r = await client.get("/api/live/transit/vehicles/mbta")
    assert r.status_code == 200
    data = r.json()
    assert "vehicles" in data
    assert "agency" in data


@pytest.mark.anyio
async def test_live_earthquakes(client: AsyncClient):
    r = await client.get("/api/live/earthquakes")
    assert r.status_code == 200
    data = r.json()
    assert "earthquakes" in data
    assert "count" in data


@pytest.mark.anyio
async def test_live_intel_endpoints(client: AsyncClient):
    # FIRMS
    r = await client.get("/api/live/firms")
    assert r.status_code == 200
    assert "hotspots" in r.json()

    # Submarine Cables
    r = await client.get("/api/live/cables")
    assert r.status_code == 200
    assert "cables" in r.json()

    # Strategic Military Installations
    r = await client.get("/api/live/installations")
    assert r.status_code == 200
    assert "installations" in r.json()

    # GNSS Jamming & Spoofing
    r = await client.get("/api/live/gnss")
    assert r.status_code == 200
    assert "zones" in r.json()

    # Air Quality AQI
    r = await client.get("/api/live/airquality")
    assert r.status_code == 200
    assert "stations" in r.json()

    # WebSDR Radio
    r = await client.get("/api/live/radio")
    assert r.status_code == 200
    assert "stations" in r.json()

    # Tactical Perimeters
    r = await client.get("/api/live/perimeters")
    assert r.status_code == 200
    assert "perimeters" in r.json()
