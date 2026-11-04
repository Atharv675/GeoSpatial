"""Security helper edge cases."""

import pytest
from pathlib import Path

from backend.shared.security import validate_geojson_type, sanitize_log_value


def test_geojson_type_whitelist():
    validate_geojson_type("Feature")
    with pytest.raises(ValueError):
        validate_geojson_type("EvilType")


def test_sanitize_log_value_truncates():
    long = "a" * 500
    out = sanitize_log_value(long, max_len=50)
    assert len(out) <= 53
    assert out.endswith("...")
