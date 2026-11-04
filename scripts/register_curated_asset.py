#!/usr/bin/env python3
"""
Register a real GeoTIFF in curated_manifest.json (local or HTTPS remote).

Example — local file from Copernicus export:
  python scripts/register_curated_asset.py ^
    --file C:\\Downloads\\B04.tif ^
    --id s2-levant-20250515-b04 ^
    --aoi-id aoi-levant ^
    --platform sentinel-2 ^
    --collection sentinel-2-l2a ^
    --datetime 2026-05-15T12:00:00Z ^
    --bands B04 ^
    --cloud-cover 12

Example — remote HTTPS (direct download URL + checksum):
  python scripts/register_curated_asset.py ^
    --id s2-levant-20250515-b04 ^
    --aoi-id aoi-levant ^
    --platform sentinel-2 ^
    --collection sentinel-2-l2a ^
    --datetime 2026-05-15T12:00:00Z ^
    --bands B04 ^
    --remote-url https://example.com/B04.tif ^
    --checksum <sha256>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "registry" / "curated_manifest.json"
DATA_ROOT = ROOT / "data"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1024 * 256):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Add asset to curated_manifest.json")
    parser.add_argument("--id", required=True, help="Unique asset id, e.g. s2-levant-w3-b04")
    parser.add_argument("--aoi-id", required=True, help="Must exist in data/registry/aois.json")
    parser.add_argument("--platform", choices=["sentinel-1", "sentinel-2"], required=True)
    parser.add_argument("--collection", required=True, help="sentinel-2-l2a or sentinel-1-grd")
    parser.add_argument("--datetime", required=True, help="ISO8601, e.g. 2026-05-15T12:00:00Z")
    parser.add_argument("--bands", nargs="+", required=True, help="e.g. B04 B08 or VV")
    parser.add_argument("--filename", help="Curated filename (default: from --file name)")
    parser.add_argument("--file", type=Path, help="Local GeoTIFF to copy into data/raw/curated/...")
    parser.add_argument("--remote-url", help="HTTPS URL for remote ingest (no --file)")
    parser.add_argument("--checksum", help="SHA256 hex (required for --remote-url; auto for --file)")
    parser.add_argument("--cloud-cover", type=float, help="S2 eo:cloud_cover property")
    parser.add_argument("--polarization", help="S1 polarization, e.g. VV")
    args = parser.parse_args()

    if bool(args.file) == bool(args.remote_url):
        print("Provide exactly one of --file or --remote-url", file=sys.stderr)
        return 1

    filename = args.filename or (args.file.name if args.file else f"{args.bands[0]}.tif")
    properties: dict = {}
    if args.cloud_cover is not None:
        properties["eo:cloud_cover"] = args.cloud_cover
    if args.platform == "sentinel-1":
        properties.setdefault("sar:instrument_mode", "IW")

    if args.file:
        if not args.file.exists():
            print(f"File not found: {args.file}", file=sys.stderr)
            return 1
        checksum = args.checksum or sha256_file(args.file)
        rel_dir = f"raw/curated/{args.collection}/{args.aoi_id}"
        dest = DATA_ROOT / rel_dir / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists() or sha256_file(dest) != checksum:
            shutil.copy2(args.file, dest)
            print(f"Copied -> {dest.relative_to(ROOT)}")
        source = {"type": "local", "path": f"{rel_dir}/{filename}".replace("\\", "/")}
    else:
        checksum = args.checksum
        if not checksum or len(checksum) != 64:
            print("--checksum required (64 hex chars) for --remote-url", file=sys.stderr)
            return 1
        source = {
            "type": "remote",
            "url": args.remote_url,
            "checksum_sha256": checksum.lower(),
        }

    entry = {
        "id": args.id,
        "platform": args.platform,
        "collection": args.collection,
        "aoi_id": args.aoi_id,
        "datetime": args.datetime,
        "filename": filename,
        "bands": args.bands,
        "source": source,
        "checksum_sha256": checksum.lower(),
        "properties": properties,
    }
    if args.polarization:
        entry["polarization"] = args.polarization

    manifest = {"version": "1", "description": "Curated Sentinel GeoTIFF assets for GeoSentinel", "assets": []}
    if MANIFEST.exists():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ids = {a["id"] for a in manifest.get("assets", [])}
    if args.id in ids:
        print(f"Asset id already in manifest: {args.id}", file=sys.stderr)
        return 1
    manifest.setdefault("assets", []).append(entry)
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Registered {args.id} ({len(manifest['assets'])} assets total)")
    print("Next: python -m backend.pipeline.run_pipeline  (or e2e_bootstrap.py --force)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
