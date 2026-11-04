"""
Lightweight STAC-compatible metadata registry.

JSON files under data/registry — designed for future STAC migration.
"""

import json
from pathlib import Path
from typing import Any

from backend.shared.config import get_settings
from backend.shared.exceptions import StorageError, ValidationError
from backend.shared.logging import get_logger
from backend.shared.security import safe_resolve_under, validate_identifier

logger = get_logger(__name__)

REGISTRY_FILENAME = "catalog.json"


class MetadataRegistry:
    """Read/write STAC-shaped catalog entries as JSON."""

    def __init__(self, registry_root: Path | None = None) -> None:
        settings = get_settings()
        self.root = registry_root or settings.registry_path
        self.catalog_path = self.root / REGISTRY_FILENAME

    def _load_catalog(self) -> dict[str, Any]:
        if not self.catalog_path.exists():
            return {
                "type": "Catalog",
                "id": "geosentinel-catalog",
                "stac_version": "1.0.0",
                "description": "GeoSentinel lightweight registry (STAC-compatible structure)",
                "collections": [],
                "items": [],
            }
        try:
            with self.catalog_path.open(encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise StorageError("Invalid registry catalog JSON") from exc
        if data.get("type") != "Catalog":
            raise ValidationError("Registry root must be type Catalog")
        return data

    def _save_catalog(self, catalog: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with self.catalog_path.open("w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2)
        logger.info("registry_catalog_saved", path=str(self.catalog_path))

    def list_items(self) -> list[dict[str, Any]]:
        """Return all STAC Item entries."""
        catalog = self._load_catalog()
        items = catalog.get("items", [])
        if not isinstance(items, list):
            raise ValidationError("Registry items must be a list")
        return items

    def get_item(self, item_id: str) -> dict[str, Any] | None:
        validate_identifier(item_id, "item_id")
        for item in self.list_items():
            if item.get("id") == item_id:
                return item
        return None

    def register_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """
        Register a STAC-compatible Item dict.

        Required fields: id, type (Item), properties, assets, geometry or bbox.
        """
        if item.get("type") != "Item":
            raise ValidationError("Registry entry must be type Item")
        item_id = item.get("id")
        if not item_id or not isinstance(item_id, str):
            raise ValidationError("Item id is required")
        validate_identifier(item_id, "item_id")

        catalog = self._load_catalog()
        items: list[dict[str, Any]] = catalog.setdefault("items", [])
        items = [i for i in items if i.get("id") != item_id]
        items.append(item)
        catalog["items"] = items
        self._save_catalog(catalog)
        return item

    def item_asset_path(self, item_id: str, asset_key: str) -> Path:
        """Resolve asset href under data root safely."""
        validate_identifier(item_id, "item_id")
        validate_identifier(asset_key, "asset_key")
        item = self.get_item(item_id)
        if not item:
            raise ValidationError(f"Unknown item: {item_id}")
        assets = item.get("assets", {})
        if asset_key not in assets:
            raise ValidationError(f"Unknown asset: {asset_key}")
        href = assets[asset_key].get("href")
        if not href or not isinstance(href, str):
            raise ValidationError("Asset href missing")
        settings = get_settings()
        return safe_resolve_under(settings.data_root, href)
