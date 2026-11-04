"""
AOI configuration loader and validator.

Loads GeoJSON polygons from data/registry/aois.json; enforces 2–3 AOI project limit.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.ingestion.models import AOIConfig, AOIRecord
from backend.shared.config import get_settings
from backend.shared.exceptions import ConfigurationError, ValidationError
from backend.shared.logging import get_logger
from backend.shared.security import validate_geojson_type

logger = get_logger(__name__)

AOI_CONFIG_FILENAME = "aois.json"


def _config_path() -> Path:
    settings = get_settings()
    return settings.registry_path / AOI_CONFIG_FILENAME


def load_aoi_config(path: Path | None = None) -> AOIConfig:
    """Load and validate AOI configuration."""
    config_path = path or _config_path()
    if not config_path.exists():
        raise ConfigurationError(f"AOI config not found: {config_path}")

    try:
        with config_path.open(encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as exc:
        raise ConfigurationError("Invalid AOI config JSON") from exc

    try:
        config = AOIConfig.model_validate(raw)
    except Exception as exc:
        raise ValidationError(f"AOI config validation failed: {exc}") from exc

    settings = get_settings()
    if len(config.aois) > settings.max_aois:
        raise ValidationError(f"AOI count exceeds max_aois={settings.max_aois}")

    for aoi in config.aois:
        validate_geojson_type("Polygon")

    logger.info("aoi_config_loaded", count=len(config.aois), path=str(config_path))
    return config


@lru_cache
def get_active_aois() -> tuple[AOIRecord, ...]:
    """Cached active AOIs."""
    config = load_aoi_config()
    return tuple(a for a in config.aois if a.active)


def get_aoi(aoi_id: str) -> AOIRecord | None:
    """Return AOI by id."""
    for aoi in get_active_aois():
        if aoi.aoi_id == aoi_id:
            return aoi
    return None


def aoi_bbox(aoi: AOIRecord) -> list[float]:
    """Compute [west, south, east, north] from Polygon coordinates."""
    coords = aoi.geometry["coordinates"][0]
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return [min(lons), min(lats), max(lons), max(lats)]


def aoi_to_feature(aoi: AOIRecord) -> dict[str, Any]:
    """GeoJSON Feature for API/frontend."""
    return {
        "type": "Feature",
        "id": aoi.aoi_id,
        "properties": {
            "aoi_id": aoi.aoi_id,
            "name": aoi.name,
            "description": aoi.description,
            "active": aoi.active,
        },
        "geometry": aoi.geometry,
    }
