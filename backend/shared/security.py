"""
Security utilities: path sanitization, input validation helpers.

OWASP-aligned: prevent path traversal, validate identifiers.
"""

import re
from pathlib import Path

# Safe identifier: alphanumeric, underscore, hyphen
IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")

# GeoJSON type whitelist
GEOJSON_TYPES = frozenset(
    {"Feature", "FeatureCollection", "Point", "Polygon", "MultiPolygon", "LineString"}
)


def safe_join(base: Path, *parts: str) -> Path:
    """
    Join path segments under base, rejecting path traversal.

    Raises ValueError if resolved path escapes base.
    """
    base_resolved = base.resolve()
    candidate = base_resolved
    for part in parts:
        if not part or part in (".", ".."):
            raise ValueError("Invalid path segment")
        if "/" in part or "\\" in part:
            raise ValueError("Path segments must not contain separators")
        candidate = (candidate / part).resolve()
    try:
        candidate.relative_to(base_resolved)
    except ValueError as exc:
        raise ValueError("Path traversal detected") from exc
    return candidate


def safe_resolve_under(base: Path, relative: str) -> Path:
    """
    Resolve a relative path (may contain forward slashes) under base.

    Used for manifest hrefs and ingest layout paths.
    """
    segments: list[str] = []
    for segment in relative.replace("\\", "/").split("/"):
        if not segment or segment == ".":
            continue
        if segment == "..":
            raise ValueError("Path traversal detected")
        segments.append(segment)
    if not segments:
        raise ValueError("Relative path is empty")
    return safe_join(base, *segments)


def validate_identifier(value: str, field_name: str = "identifier") -> str:
    """Validate a safe filesystem/API identifier."""
    if not value or not IDENTIFIER_PATTERN.match(value):
        raise ValueError(f"Invalid {field_name}: must match [a-zA-Z0-9_-] (1-128 chars)")
    return value


def validate_geojson_type(geojson_type: str | None) -> None:
    """Validate GeoJSON type field when present."""
    if geojson_type is not None and geojson_type not in GEOJSON_TYPES:
        raise ValueError(f"Unsupported GeoJSON type: {geojson_type}")


def sanitize_log_value(value: str, max_len: int = 200) -> str:
    """Truncate and strip control chars for safe logging."""
    cleaned = "".join(c for c in value if c.isprintable() or c in " \t")
    if len(cleaned) > max_len:
        return cleaned[:max_len] + "..."
    return cleaned
