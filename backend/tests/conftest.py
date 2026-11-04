"""Pytest fixtures."""

import os
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Test env before app import
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("DATA_ROOT", str(Path(__file__).resolve().parents[2] / "data"))
os.environ.setdefault("REGISTRY_PATH", str(Path(__file__).resolve().parents[2] / "data" / "registry"))

from backend.main import create_app  # noqa: E402
from backend.storage.database import Base  # noqa: E402


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def tmp_registry(tmp_path: Path) -> Path:
    reg = tmp_path / "registry"
    reg.mkdir()
    catalog = {
        "type": "Catalog",
        "id": "test-catalog",
        "stac_version": "1.0.0",
        "items": [],
    }
    import json

    (reg / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
    return reg
