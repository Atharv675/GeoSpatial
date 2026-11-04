"""
Secure HTTP client for OSINT feed retrieval.

HTTPS only, timeouts, response size limits, no shell execution.
"""

import json
from typing import Any

import httpx

from backend.shared.exceptions import ValidationError
from backend.shared.logging import get_logger

logger = get_logger(__name__)

MAX_RESPONSE_BYTES = 5 * 1024 * 1024
DEFAULT_TIMEOUT = 30.0


def fetch_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> Any:
    """GET JSON from HTTPS endpoint with validation."""
    if not url.lower().startswith("https://"):
        raise ValidationError("OSINT feeds must use HTTPS")
    with httpx.Client(timeout=timeout, follow_redirects=True, verify=True) as client:
        response = client.get(url, params=params, headers=headers or {})
        response.raise_for_status()
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise ValidationError("OSINT response exceeds size limit")
        return response.json()


def fetch_text(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """GET text (e.g. FIRMS CSV) from HTTPS endpoint."""
    if not url.lower().startswith("https://"):
        raise ValidationError("OSINT feeds must use HTTPS")
    with httpx.Client(timeout=timeout, follow_redirects=True, verify=True) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise ValidationError("OSINT response exceeds size limit")
        return response.text


def save_events_json(path: Any, events: list[dict[str, Any]]) -> None:
    """Persist normalized events list to JSON."""
    from pathlib import Path

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {"events": events, "count": len(events)}
    p.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    logger.info("osint_events_saved", path=str(p), count=len(events))
