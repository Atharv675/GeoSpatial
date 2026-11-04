#!/usr/bin/env python3
"""Initialize the lightweight STAC-compatible metadata registry."""

import json
import sys
from pathlib import Path

REGISTRY_TEMPLATE = {
    "type": "Catalog",
    "id": "geosentinel-catalog",
    "stac_version": "1.0.0",
    "description": "GeoSentinel curated imagery registry — designed for future STAC migration",
    "scope": {
        "max_aois": 3,
        "time_range_days": 30,
        "tile_size": 512,
        "update_frequency": "weekly",
    },
    "collections": [
        {
            "type": "Collection",
            "id": "sentinel-2-l2a",
            "title": "Sentinel-2 L2A (curated)",
            "description": "Optical imagery for NDVI, NDWI, NBR analysis",
        },
        {
            "type": "Collection",
            "id": "sentinel-1-grd",
            "title": "Sentinel-1 GRD (curated)",
            "description": "SAR imagery for temporal differencing",
        },
    ],
    "items": [],
}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    registry_dir = root / "data" / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    catalog_path = registry_dir / "catalog.json"
    if catalog_path.exists():
        print(f"Registry already exists: {catalog_path}")
        return 0
    catalog_path.write_text(json.dumps(REGISTRY_TEMPLATE, indent=2), encoding="utf-8")
    print(f"Created registry: {catalog_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
