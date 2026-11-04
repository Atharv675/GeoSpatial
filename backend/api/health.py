"""Health and readiness endpoints."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.config import Settings, get_settings
from backend.storage.database import check_database_connection, get_db_session
from backend.storage.registry import MetadataRegistry

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe — process is running."""
    return {"status": "ok"}


def _settings() -> Settings:
    return get_settings()


@router.get("/ready")
async def ready(
    settings: Settings = Depends(_settings),
    _session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Readiness probe — DB and registry accessible."""
    db_ok = await check_database_connection()
    registry_ok = False
    try:
        reg = MetadataRegistry()
        reg.list_items()
        registry_ok = True
    except Exception:
        registry_ok = False

    status = "ready" if db_ok and registry_ok else "degraded"
    return {
        "status": status,
        "database": db_ok,
        "registry": registry_ok,
        "app": settings.app_name,
        "scope": {
            "max_aois": settings.max_aois,
            "time_range_days": settings.time_range_days,
            "tile_size": settings.tile_size,
        },
    }
