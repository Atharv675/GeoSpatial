"""
Curated imagery manifest loader.

Only manifest-listed assets are ingested — no open-ended catalog search.
"""

import json
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

from backend.ingestion.models import CuratedAsset, CuratedManifest, Platform
from backend.shared.config import get_settings
from backend.shared.exceptions import ConfigurationError, ValidationError
from backend.shared.logging import get_logger

logger = get_logger(__name__)

MANIFEST_FILENAME = "curated_manifest.json"


def _manifest_path() -> Path:
    settings = get_settings()
    return settings.registry_path / MANIFEST_FILENAME


def load_curated_manifest(path: Path | None = None) -> CuratedManifest:
    """Load curated manifest from registry."""
    manifest_path = path or _manifest_path()
    if not manifest_path.exists():
        raise ConfigurationError(f"Curated manifest not found: {manifest_path}")

    try:
        with manifest_path.open(encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as exc:
        raise ConfigurationError("Invalid curated manifest JSON") from exc

    try:
        manifest = CuratedManifest.model_validate(raw)
    except Exception as exc:
        raise ValidationError(f"Manifest validation failed: {exc}") from exc

    logger.info(
        "curated_manifest_loaded",
        assets=len(manifest.assets),
        path=str(manifest_path),
    )
    return manifest


def filter_assets_by_time_range(
    manifest: CuratedManifest,
    days: int | None = None,
    reference: datetime | None = None,
) -> list[CuratedAsset]:
    """Keep assets within the project time window (default: settings.time_range_days)."""
    settings = get_settings()
    window_days = days if days is not None else settings.time_range_days
    ref = reference or datetime.now(timezone.utc)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    cutoff = ref - timedelta(days=window_days)

    filtered = []
    for asset in manifest.assets:
        dt = asset.datetime
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt >= cutoff:
            filtered.append(asset)
    return filtered


def assets_for_aoi(manifest: CuratedManifest, aoi_id: str) -> list[CuratedAsset]:
    return [a for a in manifest.assets if a.aoi_id == aoi_id]


def assets_for_platform(manifest: CuratedManifest, platform: Platform) -> list[CuratedAsset]:
    return [a for a in manifest.assets if a.platform == platform]


@lru_cache
def get_manifest_asset_ids() -> frozenset[str]:
    return frozenset(a.id for a in load_curated_manifest().assets)
