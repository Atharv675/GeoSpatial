"""Metadata registry unit tests."""

import json
from pathlib import Path

import pytest

from backend.storage.registry import MetadataRegistry
from backend.shared.exceptions import ValidationError


def test_register_and_get_item(tmp_path: Path, monkeypatch):
    reg_dir = tmp_path / "registry"
    reg_dir.mkdir()
    monkeypatch.setenv("REGISTRY_PATH", str(reg_dir))
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))

    from backend.shared.config import get_settings

    get_settings.cache_clear()

    reg = MetadataRegistry(reg_dir)
    item = {
        "type": "Item",
        "id": "test-item-1",
        "properties": {"datetime": "2025-01-01T00:00:00Z"},
        "assets": {"data": {"href": "raw/test.tif", "type": "image/tiff"}},
    }
    reg.register_item(item)
    loaded = reg.get_item("test-item-1")
    assert loaded is not None
    assert loaded["id"] == "test-item-1"


def test_reject_invalid_item_type(tmp_path: Path):
    reg = MetadataRegistry(tmp_path / "registry")
    with pytest.raises(ValidationError):
        reg.register_item({"type": "Collection", "id": "bad"})


def test_load_catalog_when_missing(tmp_path: Path):
    reg = MetadataRegistry(tmp_path / "registry")
    items = reg.list_items()
    assert items == []
