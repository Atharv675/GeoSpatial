"""Resumable HTTPS download tests."""

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.ingestion.download import download_remote_asset


def _mock_stream_response(content: bytes, status_code: int = 200):
    response = MagicMock()
    response.status_code = status_code
    response.raise_for_status = MagicMock()

    def iter_bytes(chunk_size=None):
        yield content

    response.iter_bytes = iter_bytes
    return response


@patch("backend.ingestion.download.httpx.Client")
def test_remote_download_with_checksum(mock_client_cls, tmp_path: Path):
    payload = b"resumable-download-content-v1"
    checksum = hashlib.sha256(payload).hexdigest()
    dest = tmp_path / "remote.tif"

    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client
    mock_client.stream.return_value.__enter__.return_value = _mock_stream_response(payload)

    result = download_remote_asset("https://example.com/asset.tif", dest, checksum)
    assert result.path.exists()
    assert result.skipped is False
    assert dest.read_bytes() == payload
