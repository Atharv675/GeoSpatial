"""Phase 2 ingestion tests."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.ingestion.aoi import get_active_aois, load_aoi_config
from backend.ingestion.download import (
    copy_local_asset,
    download_remote_asset,
    sha256_file,
    verify_checksum,
)
from backend.ingestion.ingest import run_ingestion
from backend.ingestion.manifest import filter_assets_by_time_range, load_curated_manifest
from backend.ingestion.models import CuratedManifest, Platform
from backend.shared.config import get_settings
from backend.shared.exceptions import ValidationError


def _clear_ingestion_caches() -> None:
    get_active_aois.cache_clear()
    get_settings.cache_clear()
    try:
        from backend.ingestion.manifest import get_manifest_asset_ids

        get_manifest_asset_ids.cache_clear()
    except Exception:
        pass


@pytest.fixture
def ingestion_env(tmp_path: Path, monkeypatch):
    data = tmp_path / "data"
    registry = data / "registry"
    registry.mkdir(parents=True)
    (data / "raw").mkdir(parents=True)

    aois_src = Path(__file__).resolve().parents[2] / "data" / "registry" / "aois.json"
    (registry / "aois.json").write_text(aois_src.read_text(encoding="utf-8"), encoding="utf-8")

    monkeypatch.setenv("DATA_ROOT", str(data))
    monkeypatch.setenv("REGISTRY_PATH", str(registry))
    _clear_ingestion_caches()
    yield data, registry
    _clear_ingestion_caches()


def test_filter_assets_within_30_days(ingestion_env):
    _, registry = ingestion_env
    now = datetime.now(timezone.utc)
    manifest_data = {
        "version": "1",
        "assets": [
            {
                "id": "recent-asset",
                "platform": "sentinel-2",
                "collection": "sentinel-2-l2a",
                "aoi_id": "aoi-levant",
                "datetime": (now - timedelta(days=5)).isoformat().replace("+00:00", "Z"),
                "filename": "x.tif",
                "bands": ["B04"],
                "source": {"type": "local", "path": "raw/curated/x.tif"},
                "checksum_sha256": "a" * 64,
            },
            {
                "id": "old-asset",
                "platform": "sentinel-2",
                "collection": "sentinel-2-l2a",
                "aoi_id": "aoi-levant",
                "datetime": (now - timedelta(days=60)).isoformat().replace("+00:00", "Z"),
                "filename": "y.tif",
                "bands": ["B04"],
                "source": {"type": "local", "path": "raw/curated/y.tif"},
                "checksum_sha256": "b" * 64,
            },
        ],
    }
    (registry / "curated_manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")
    _clear_ingestion_caches()
    manifest = load_curated_manifest()
    filtered = filter_assets_by_time_range(manifest, reference=now)
    assert len(filtered) == 1
    assert filtered[0].id == "recent-asset"


def test_checksum_verification(tmp_path: Path):
    f = tmp_path / "sample.bin"
    f.write_bytes(b"test-payload")
    digest = sha256_file(f)
    verify_checksum(f, digest)
    with pytest.raises(ValidationError):
        verify_checksum(f, "0" * 64)


def test_local_copy_and_skip(ingestion_env):
    data, _ = ingestion_env
    src_rel = "raw/curated/test.tif"
    src = data / src_rel
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_bytes(b"local-ingest-test")
    checksum = sha256_file(src)
    dest = data / "raw" / "dest.tif"

    r1 = copy_local_asset(data, src_rel, dest, checksum)
    assert r1.skipped is False
    r2 = copy_local_asset(data, src_rel, dest, checksum)
    assert r2.skipped is True


def test_remote_download_rejects_non_https(tmp_path: Path):
    dest = tmp_path / "out.tif"
    with pytest.raises(ValidationError):
        download_remote_asset("http://example.com/file.tif", dest, "a" * 64)


def test_run_ingestion_registers_items(ingestion_env):
    data, registry = ingestion_env
    now = datetime.now(timezone.utc)

    assets = []
    for i, (platform, coll, aoi) in enumerate(
        [
            ("sentinel-2", "sentinel-2-l2a", "aoi-levant"),
            ("sentinel-1", "sentinel-1-grd", "aoi-levant"),
        ]
    ):
        rel = f"raw/curated/{platform}/{aoi}/f{i}.tif"
        payload = f"payload-{i}".encode()
        path = data / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        from backend.ingestion.download import sha256_file

        assets.append(
            {
                "id": f"asset-{i}",
                "platform": platform,
                "collection": coll,
                "aoi_id": aoi,
                "datetime": (now - timedelta(days=7 + i)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "filename": f"f{i}.tif",
                "bands": ["B04"] if platform == "sentinel-2" else ["VV"],
                "source": {"type": "local", "path": rel},
                "checksum_sha256": sha256_file(path),
                **({"polarization": "VV"} if platform == "sentinel-1" else {}),
            }
        )

    (registry / "curated_manifest.json").write_text(
        json.dumps({"version": "1", "assets": assets}),
        encoding="utf-8",
    )
    _clear_ingestion_caches()

    result = run_ingestion(run_id="test-run")
    assert result.assets_ok == 2
    assert result.assets_failed == 0

    from backend.storage.registry import MetadataRegistry

    reg = MetadataRegistry(registry)
    items = reg.list_items()
    assert len(items) >= 2


@pytest.mark.anyio
async def test_api_list_aois(client, ingestion_env):
    _clear_ingestion_caches()
    r = await client.get("/api/v1/aois")
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "FeatureCollection"
    assert body["count"] == 2


@pytest.mark.anyio
async def test_api_ingestion_run(client, ingestion_env):
    data, registry = ingestion_env
    now = datetime.now(timezone.utc)
    rel = "raw/curated/sentinel-2/aoi-levant/run.tif"
    path = data / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"api-run-test")
    from backend.ingestion.download import sha256_file

    manifest = {
        "version": "1",
        "assets": [
            {
                "id": "api-run-asset",
                "platform": "sentinel-2",
                "collection": "sentinel-2-l2a",
                "aoi_id": "aoi-levant",
                "datetime": (now - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "filename": "run.tif",
                "bands": ["B04"],
                "source": {"type": "local", "path": rel},
                "checksum_sha256": sha256_file(path),
            }
        ],
    }
    (registry / "curated_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    _clear_ingestion_caches()

    r = await client.post("/api/v1/ingestion/run", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["assets_ok"] == 1
