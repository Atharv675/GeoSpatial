"""Application-specific exceptions."""

from typing import Any


class GeoSentinelError(Exception):
    """Base application error."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(GeoSentinelError):
    """Invalid or missing configuration."""


class ValidationError(GeoSentinelError):
    """Input validation failure."""


class StorageError(GeoSentinelError):
    """Database or filesystem storage error."""
