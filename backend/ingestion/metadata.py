"""
Metadata extraction for ingested assets.

Builds STAC-compatible Item records from manifest + AOI + file stats.
Raster band parsing deferred to Phase 3 (Rasterio).
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.ingestion.aoi import aoi_bbox, get_aoi
from backend.ingestion.models import CuratedAsset, Platform
from backend.shared.logging import get_logger

logger = get_logger(__name__)


def extract_file_metadata(path: Path) -> dict[str, Any]:
    """Extract safe filesystem metadata — does not trust GeoTIFF internal tags yet."""
    stat = path.stat()
    return {
        "file:size_bytes": stat.st_size,
        "file:modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        "file:name": path.name,
    }


def build_stac_item(asset: CuratedAsset, output_path: Path, href_relative: str) -> dict[str, Any]:
    """
    Construct a STAC Item for registry registration.

    href_relative is path relative to data_root (e.g. raw/sentinel-2/.../file.tif).
    """
    aoi = get_aoi(asset.aoi_id)
    bbox = aoi_bbox(aoi) if aoi else None

    props: dict[str, Any] = {
        "datetime": asset.datetime.isoformat().replace("+00:00", "Z"),
        "platform": asset.platform.value,
        "gs:collection": asset.collection,
        "gs:aoi_id": asset.aoi_id,
        "gs:curated": True,
        "gs:ingested_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        **extract_file_metadata(output_path),
        **asset.properties,
    }
    if asset.bands:
        props["gs:bands"] = asset.bands
    if asset.polarization:
        props["sar:polarization"] = asset.polarization

    item: dict[str, Any] = {
        "type": "Item",
        "stac_version": "1.0.0",
        "id": asset.id,
        "collection": asset.collection,
        "properties": props,
        "assets": {
            "data": {
                "href": href_relative.replace("\\", "/"),
                "type": "image/tiff",
                "roles": ["data"],
            }
        },
    }
    if aoi:
        item["geometry"] = aoi.geometry
    if bbox:
        item["bbox"] = bbox

    if asset.platform == Platform.SENTINEL_1:
        item["properties"]["sar:instrument_mode"] = props.get("sar:instrument_mode", "IW")
        item["properties"]["gs:product_type"] = "GRD"
    elif asset.platform == Platform.SENTINEL_2:
        item["properties"]["eo:cloud_cover"] = props.get("eo:cloud_cover", 0)
        item["properties"]["gs:product_type"] = "L2A"

    logger.info("metadata_extracted", asset_id=asset.id, bytes=props.get("file:size_bytes"))
    return item
