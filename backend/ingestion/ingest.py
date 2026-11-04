"""
Ingestion orchestrator — curated Sentinel-1 and Sentinel-2 assets only.

Validates AOIs, filters manifest to time range, ingests per platform, persists state.
"""

import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.ingestion.aoi import get_active_aois, load_aoi_config
from backend.ingestion.manifest import filter_assets_by_time_range, load_curated_manifest
from backend.ingestion.models import (
    AssetIngestResult,
    AssetIngestStatus,
    CuratedAsset,
    IngestionResult,
    Platform,
)
from backend.ingestion.sentinel1 import ingest_sentinel1_asset
from backend.ingestion.sentinel2 import ingest_sentinel2_asset
from backend.shared.config import get_settings
from backend.shared.exceptions import ValidationError
from backend.shared.logging import get_logger

logger = get_logger(__name__)

STATE_FILENAME = "ingest_state.json"


def _state_path() -> Path:
    return get_settings().resolve_data_path("raw") / STATE_FILENAME


def _load_state() -> dict[str, Any]:
    path = _state_path()
    if not path.exists():
        return {"runs": []}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _save_state(state: dict[str, Any]) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def _validate_aoi_references(assets: list[CuratedAsset]) -> None:
    active_ids = {a.aoi_id for a in get_active_aois()}
    for asset in assets:
        if asset.aoi_id not in active_ids:
            raise ValidationError(f"Asset {asset.id} references unknown or inactive AOI: {asset.aoi_id}")


def _ingest_asset(asset: CuratedAsset) -> AssetIngestResult:
    if asset.platform == Platform.SENTINEL_1:
        return ingest_sentinel1_asset(asset)
    if asset.platform == Platform.SENTINEL_2:
        return ingest_sentinel2_asset(asset)
    return AssetIngestResult(
        asset_id=asset.id,
        status=AssetIngestStatus.FAILED,
        message=f"Unsupported platform: {asset.platform}",
    )


def run_ingestion(run_id: str | None = None) -> IngestionResult:
    """
    Run full curated ingestion for all in-scope assets.

    Returns structured result; failed assets do not stop remaining assets.
    """
    started = datetime.now(timezone.utc)
    run_id = run_id or started.strftime("%Y%m%dT%H%M%SZ")

    load_aoi_config()
    manifest = load_curated_manifest()
    assets = filter_assets_by_time_range(manifest)
    _validate_aoi_references(assets)

    logger.info(
        "ingestion_start",
        run_id=run_id,
        assets=len(assets),
        aois=len(get_active_aois()),
    )

    results: list[AssetIngestResult] = []
    for asset in assets:
        results.append(_ingest_asset(asset))

    completed = datetime.now(timezone.utc)
    ok_statuses = {
        AssetIngestStatus.DOWNLOADED,
        AssetIngestStatus.COPIED,
        AssetIngestStatus.SKIPPED,
    }
    assets_ok = sum(1 for r in results if r.status in ok_statuses)
    assets_failed = sum(1 for r in results if r.status == AssetIngestStatus.FAILED)

    result = IngestionResult(
        run_id=run_id,
        started_at=started,
        completed_at=completed,
        assets_total=len(assets),
        assets_ok=assets_ok,
        assets_failed=assets_failed,
        results=results,
    )

    state = _load_state()
    state.setdefault("runs", []).append(
        {
            "run_id": run_id,
            "started_at": started.isoformat(),
            "completed_at": completed.isoformat(),
            "assets_total": result.assets_total,
            "assets_ok": result.assets_ok,
            "assets_failed": result.assets_failed,
        }
    )
    state["last_run"] = result.model_dump(mode="json")
    _save_state(state)

    logger.info(
        "ingestion_complete",
        run_id=run_id,
        ok=assets_ok,
        failed=assets_failed,
    )
    return result


def get_last_ingestion_summary() -> dict[str, Any] | None:
    state = _load_state()
    return state.get("last_run")
