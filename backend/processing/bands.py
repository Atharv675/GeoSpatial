"""
Band pairing for curated Sentinel-2 assets.

Groups registry items by AOI and acquisition date for index computation.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from backend.processing.indices import classify_band
from backend.shared.config import get_settings


@dataclass
class BandObservation:
    item_id: str
    band: str
    role: str
    normalized_path: Path
    datetime: datetime


@dataclass
class AcquisitionGroup:
    aoi_id: str
    date_key: str
    datetime: datetime
    observations: list[BandObservation] = field(default_factory=list)

    def band_array(self, role: str) -> BandObservation | None:
        for obs in self.observations:
            if obs.role == role:
                return obs
        return None


def _parse_datetime(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))


def _date_key(dt: datetime) -> str:
    return dt.strftime("%Y%m%d")


def normalized_path_for_item(item: dict) -> Path | None:
    """Resolve preprocessed normalized.tif for registry item."""
    settings = get_settings()
    item_id = item["id"]
    props = item.get("properties", {})
    aoi_id = props.get("gs:aoi_id", "")
    collection = item.get("collection", props.get("gs:collection", ""))
    if not aoi_id or not collection:
        return None
    rel = f"processed/{collection}/{aoi_id}/{item_id}/normalized.tif"
    path = settings.resolve_data_path(rel)
    return path if path.exists() else None


def group_optical_acquisitions(items: list[dict]) -> list[AcquisitionGroup]:
    """Group Sentinel-2 items by AOI and acquisition date."""
    buckets: dict[tuple[str, str], AcquisitionGroup] = {}

    for item in items:
        props = item.get("properties", {})
        if props.get("platform") != "sentinel-2":
            continue
        norm = normalized_path_for_item(item)
        if not norm:
            continue
        aoi_id = props.get("gs:aoi_id", "")
        dt_str = props.get("datetime", "")
        if not aoi_id or not dt_str:
            continue
        dt = _parse_datetime(dt_str)
        key = (aoi_id, _date_key(dt))
        if key not in buckets:
            buckets[key] = AcquisitionGroup(aoi_id=aoi_id, date_key=key[1], datetime=dt)
        bands = props.get("gs:bands", [])
        if not bands:
            continue
        band_name = bands[0]
        role = classify_band(band_name)
        if not role:
            continue
        buckets[key].observations.append(
            BandObservation(
                item_id=item["id"],
                band=band_name,
                role=role,
                normalized_path=norm,
                datetime=dt,
            )
        )

    return sorted(buckets.values(), key=lambda g: (g.aoi_id, g.datetime))
