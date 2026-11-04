"""
Secure, resumable file acquisition for curated assets.

- HTTPS only for remote sources (SSL verification enabled)
- Atomic writes via temp + rename
- SHA-256 verification
- HTTP Range resume when supported
"""

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from backend.shared.exceptions import ValidationError
from backend.shared.logging import get_logger
from backend.shared.security import safe_resolve_under

logger = get_logger(__name__)

CHUNK_SIZE = 1024 * 256
STATE_SUFFIX = ".download.json"
PART_SUFFIX = ".part"


@dataclass
class DownloadResult:
    path: Path
    bytes_written: int
    resumed: bool
    skipped: bool


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksum(path: Path, expected: str) -> None:
    actual = sha256_file(path)
    if actual.lower() != expected.lower():
        raise ValidationError(
            f"Checksum mismatch for {path.name}: expected {expected[:12]}… got {actual[:12]}…"
        )


def _state_path(dest: Path) -> Path:
    return dest.with_suffix(dest.suffix + STATE_SUFFIX)


def _part_path(dest: Path) -> Path:
    return dest.with_suffix(dest.suffix + PART_SUFFIX)


def _load_state(state_file: Path) -> dict[str, Any]:
    if not state_file.exists():
        return {}
    try:
        with state_file.open(encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def _save_state(state_file: Path, state: dict[str, Any]) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with state_file.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def _validate_remote_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValidationError("Only HTTPS URLs are permitted")
    if not parsed.netloc:
        raise ValidationError("Invalid URL host")


def copy_local_asset(
    data_root: Path,
    source_relative: str,
    dest: Path,
    expected_checksum: str,
) -> DownloadResult:
    """Copy a curated local file into the ingest layout with checksum verification."""
    source = safe_resolve_under(data_root, source_relative)
    if not source.exists() or not source.is_file():
        raise ValidationError(f"Local source not found: {source_relative}")

    verify_checksum(source, expected_checksum)
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        try:
            verify_checksum(dest, expected_checksum)
            return DownloadResult(path=dest, bytes_written=dest.stat().st_size, resumed=False, skipped=True)
        except ValidationError:
            dest.unlink(missing_ok=True)

    tmp = dest.with_suffix(dest.suffix + ".tmp")
    shutil.copy2(source, tmp)
    verify_checksum(tmp, expected_checksum)
    tmp.replace(dest)
    size = dest.stat().st_size
    logger.info("local_asset_copied", source=source_relative, dest=str(dest), bytes=size)
    return DownloadResult(path=dest, bytes_written=size, resumed=False, skipped=False)


def download_remote_asset(
    url: str,
    dest: Path,
    expected_checksum: str,
    timeout: float = 120.0,
) -> DownloadResult:
    """
    Download remote asset with resume support and checksum validation.

    Uses a .part file and JSON state for offset tracking.
    """
    _validate_remote_url(url)
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        try:
            verify_checksum(dest, expected_checksum)
            return DownloadResult(path=dest, bytes_written=dest.stat().st_size, resumed=False, skipped=True)
        except ValidationError:
            dest.unlink(missing_ok=True)

    part = _part_path(dest)
    state_file = _state_path(dest)
    state = _load_state(state_file)
    offset = 0
    resumed = False

    if part.exists() and state.get("url") == url and state.get("checksum") == expected_checksum:
        offset = int(state.get("offset", 0))
        resumed = offset > 0

    headers: dict[str, str] = {}
    if offset > 0:
        headers["Range"] = f"bytes={offset}-"

    state = {"url": url, "checksum": expected_checksum, "offset": offset, "dest": str(dest)}
    _save_state(state_file, state)

    bytes_written = offset
    with httpx.Client(timeout=timeout, follow_redirects=True, verify=True) as client:
        with client.stream("GET", url, headers=headers) as response:
            if offset > 0 and response.status_code == 416:
                part.unlink(missing_ok=True)
                offset = 0
                resumed = False
                state["offset"] = 0
                with client.stream("GET", url) as retry_response:
                    retry_response.raise_for_status()
                    bytes_written = _write_stream(
                        retry_response, part, offset=0, state_file=state_file, state=state
                    )
            elif offset > 0 and response.status_code not in (200, 206):
                part.unlink(missing_ok=True)
                offset = 0
                resumed = False
                state["offset"] = 0
                with client.stream("GET", url) as retry_response:
                    retry_response.raise_for_status()
                    bytes_written = _write_stream(
                        retry_response, part, offset=0, state_file=state_file, state=state
                    )
            else:
                response.raise_for_status()
                if response.status_code == 200 and offset > 0:
                    part.unlink(missing_ok=True)
                    offset = 0
                    resumed = False
                    state["offset"] = 0
                bytes_written = _write_stream(
                    response, part, offset=offset, state_file=state_file, state=state
                )

    verify_checksum(part, expected_checksum)
    part.replace(dest)
    state_file.unlink(missing_ok=True)
    logger.info(
        "remote_asset_downloaded",
        url_host=urlparse(url).netloc,
        dest=str(dest),
        bytes=bytes_written,
        resumed=resumed,
    )
    return DownloadResult(path=dest, bytes_written=bytes_written, resumed=resumed, skipped=False)


def _write_stream(
    response: httpx.Response,
    part: Path,
    offset: int = 0,
    state_file: Path | None = None,
    state: dict[str, Any] | None = None,
) -> int:
    mode = "ab" if offset > 0 else "wb"
    written = offset
    with part.open(mode) as out:
        for chunk in response.iter_bytes(chunk_size=CHUNK_SIZE):
            out.write(chunk)
            written += len(chunk)
            if state_file is not None and state is not None:
                state["offset"] = written
                _save_state(state_file, state)
    return written
