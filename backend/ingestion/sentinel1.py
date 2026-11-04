"""
Sentinel-1 GRD curated ingestion.

Simplified scope: ingest curated SAR rasters for temporal differencing (Phase 4).
No coherence, polarimetry, or SAR ML pipelines.
"""

from pathlib import Path

from backend.ingestion.download import copy_local_asset, download_remote_asset
from backend.ingestion.metadata import build_stac_item
from backend.ingestion.models import (
    AssetIngestResult,
    AssetIngestStatus,
    CuratedAsset,
    LocalSource,
    RemoteSource,
)
from backend.shared.config import get_settings
from backend.shared.exceptions import ValidationError
from backend.shared.logging import get_logger

logger = get_logger(__name__)

COLLECTION = "sentinel-1-grd"


def output_path_for_asset(asset: CuratedAsset) -> tuple[Path, str]:
    """Return absolute path and data-root-relative href."""
    settings = get_settings()
    date_str = asset.datetime.strftime("%Y%m%d")
    rel = f"raw/{COLLECTION}/{asset.aoi_id}/{date_str}/{asset.filename}"
    return settings.resolve_data_path(rel), rel


def ingest_sentinel1_asset(asset: CuratedAsset) -> AssetIngestResult:
    """Ingest one curated Sentinel-1 asset."""
    if asset.collection != COLLECTION:
        raise ValidationError(f"Asset {asset.id} is not {COLLECTION}")

    settings = get_settings()
    dest, href_rel = output_path_for_asset(asset)
    checksum = asset.checksum_sha256
    if not checksum:
        return AssetIngestResult(
            asset_id=asset.id,
            status=AssetIngestStatus.FAILED,
            message="Missing checksum",
        )

    try:
        if isinstance(asset.source, LocalSource):
            result = copy_local_asset(
                settings.data_root,
                asset.source.path,
                dest,
                checksum,
            )
            status = AssetIngestStatus.SKIPPED if result.skipped else AssetIngestStatus.COPIED
        else:
            assert isinstance(asset.source, RemoteSource)
            result = download_remote_asset(
                asset.source.url,
                dest,
                checksum,
            )
            status = AssetIngestStatus.SKIPPED if result.skipped else AssetIngestStatus.DOWNLOADED

        item = build_stac_item(asset, dest, href_rel)
        from backend.storage.registry import MetadataRegistry

        MetadataRegistry().register_item(item)

        logger.info("sentinel1_ingest_ok", asset_id=asset.id, status=status.value)
        return AssetIngestResult(
            asset_id=asset.id,
            status=status,
            registry_item_id=asset.id,
            output_path=href_rel,
        )
    except Exception as exc:
        logger.error("sentinel1_ingest_failed", asset_id=asset.id, error=type(exc).__name__)
        return AssetIngestResult(
            asset_id=asset.id,
            status=AssetIngestStatus.FAILED,
            message=str(exc)[:500],
        )
