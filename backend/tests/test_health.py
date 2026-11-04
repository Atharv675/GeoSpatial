"""API health endpoint tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_root(client: AsyncClient):
    r = await client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["service"] == "GeoSentinel"
    assert "api" in data


@pytest.mark.anyio
async def test_health_liveness(client: AsyncClient):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.anyio
async def test_registry_list_empty(client: AsyncClient):
    r = await client.get("/api/v1/registry/items")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "count" in body
