"""Configuration and security utility tests."""

import pytest
from pathlib import Path

from backend.shared.config import Settings
from backend.shared.security import safe_join, safe_resolve_under, validate_identifier


def test_settings_scope_limits():
    s = Settings(
        postgres_password="test",
        max_aois=3,
        time_range_days=30,
        tile_size=512,
    )
    assert s.max_aois == 3
    assert s.time_range_days == 30
    assert s.tile_size == 512


def test_cors_origin_list():
    s = Settings(postgres_password="test", cors_origins="http://a.com, http://b.com")
    assert len(s.cors_origin_list) == 2


def test_validate_identifier_valid():
    assert validate_identifier("sentinel-2_aoi1") == "sentinel-2_aoi1"


def test_validate_identifier_invalid():
    with pytest.raises(ValueError):
        validate_identifier("../etc/passwd")


def test_safe_join_rejects_traversal(tmp_path: Path):
    base = tmp_path / "data"
    base.mkdir()
    with pytest.raises(ValueError):
        safe_join(base, "..", "secret")


def test_safe_resolve_under_nested(tmp_path: Path):
    base = tmp_path / "data"
    base.mkdir()
    resolved = safe_resolve_under(base, "raw/curated/test.tif")
    assert resolved == (base / "raw" / "curated" / "test.tif").resolve()


def test_safe_resolve_under_rejects_dotdot(tmp_path: Path):
    base = tmp_path / "data"
    base.mkdir()
    with pytest.raises(ValueError):
        safe_resolve_under(base, "raw/../secret")
