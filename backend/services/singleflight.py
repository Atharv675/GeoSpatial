"""In-memory Singleflight Cache & Guardrails for Live Feeds.

Coalesces identical concurrent upstream requests, manages TTL caching with
stale-while-revalidate support on upstream failure, and enforces strict SSRF
allowlists and size caps (<= 16MB).
"""

from __future__ import annotations

import asyncio
import ipaddress
import time
from typing import Any, Callable, Coroutine, Dict, Optional, Set
from urllib.parse import urlparse

import httpx
from backend.shared.logging import get_logger

logger = get_logger(__name__)

# Maximum response size allowed through proxies (16 MB)
MAX_RESPONSE_SIZE = 16 * 1024 * 1024

# Strict host allowlists for upstream proxies
ALLOWED_HOSTS: Set[str] = {
    # Flight & Military
    "opensky-network.org",
    "api.adsb.lol",
    "api.adsbdb.com",
    # Space & Orbital
    "celestrak.org",
    "www.celestrak.org",
    "ll.thespacedevs.com",
    # Weather & Earth Observation
    "nowcoast.noaa.gov",
    "www.nhc.noaa.gov",
    "api.open-meteo.com",
    "earthquake.usgs.gov",
    # Public CCTV Catalogs & Feeds
    "data.austintexas.gov",
    "its.txdot.gov",
    "cwwp2.dot.ca.gov",
    "s3-eu-west-1.amazonaws.com",  # TfL JamCams CDN
    "api.tfl.gov.uk",
    "511on.ca",
    "images.drivebc.ca",
    "tie.digitraffic.fi",
    "weathercam.digitraffic.fi",
    "webkamera.vegvesen.no",
    # Transit Agencies
    "cdn.mbta.com",
    "opendata.toronto.ca",
    "data.texas.gov",
    "api.entur.io",
    "realtime.hsl.fi",
}


def is_allowed_host(url: str) -> bool:
    """Validate whether the URL host is strictly allowlisted and not a private/loopback IP."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = (parsed.hostname or "").lower()
        if not hostname:
            return False

        # Block localhost / loopback / private IP SSRF
        if hostname in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
            return False
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
                return False
        except ValueError:
            pass  # It is a domain name, not a raw IP

        return hostname in ALLOWED_HOSTS
    except Exception:
        return False


class CacheEntry:
    __slots__ = ("data", "timestamp", "ttl")

    def __init__(self, data: Any, ttl: float):
        self.data = data
        self.timestamp = time.monotonic()
        self.ttl = ttl

    @property
    def is_expired(self) -> bool:
        return (time.monotonic() - self.timestamp) > self.ttl


class SingleflightCache:
    """Async singleflight cache that deduplicates identical concurrent upstream fetches

    and provides graceful stale-while-revalidate fallbacks.
    """

    def __init__(self) -> None:
        self._cache: Dict[str, CacheEntry] = {}
        self._in_flight: Dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()

    async def execute(
        self,
        key: str,
        fetcher: Callable[[], Coroutine[Any, Any, Any]],
        ttl_seconds: float = 60.0,
        allow_stale_on_error: bool = True,
        timeout_seconds: float = 15.0,
    ) -> Any:
        # Check valid cache hit
        async with self._lock:
            cached = self._cache.get(key)
            if cached and not cached.is_expired:
                return cached.data

            # If there is already an in-flight future, wait on it
            if key in self._in_flight:
                fut = self._in_flight[key]
                wait_existing = True
            else:
                fut = asyncio.get_running_loop().create_future()
                self._in_flight[key] = fut
                wait_existing = False

        if wait_existing:
            return await fut

        # Execute the fetcher as the single responsible worker
        try:
            result = await asyncio.wait_for(fetcher(), timeout=timeout_seconds)
            async with self._lock:
                self._cache[key] = CacheEntry(result, ttl_seconds)
                if not fut.done():
                    fut.set_result(result)
            return result
        except Exception as exc:
            logger.warning("singleflight_fetch_failed", key=key, error=str(exc))
            # Fallback to stale cached data if allowed and available
            async with self._lock:
                stale = self._cache.get(key)
                if allow_stale_on_error and stale is not None:
                    logger.info("singleflight_served_stale", key=key)
                    if not fut.done():
                        fut.set_result(stale.data)
                    return stale.data

                if not fut.done():
                    fut.set_exception(exc)
            raise exc
        finally:
            async with self._lock:
                self._in_flight.pop(key, None)

    def set(self, key: str, data: Any, ttl_seconds: float = 60.0) -> None:
        self._cache[key] = CacheEntry(data, ttl_seconds)

    def get(self, key: str) -> Optional[Any]:
        cached = self._cache.get(key)
        if cached and not cached.is_expired:
            return cached.data
        return None

    def clear(self) -> None:
        self._cache.clear()


# Global in-memory cache instance
singleflight = SingleflightCache()


async def safe_http_get(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 12.0,
    as_json: bool = True,
) -> Any:
    """Safe HTTP GET with host allowlist validation, timeout, and response body size limit."""
    if not is_allowed_host(url):
        raise ValueError(f"Forbidden proxy destination: host not in allowlist for URL {url}")

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()

        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > MAX_RESPONSE_SIZE:
            raise ValueError(f"Response exceeds maximum allowed size of {MAX_RESPONSE_SIZE} bytes")

        body = response.content
        if len(body) > MAX_RESPONSE_SIZE:
            raise ValueError(f"Response exceeds maximum allowed size of {MAX_RESPONSE_SIZE} bytes")

        if as_json:
            return response.json()
        return body
