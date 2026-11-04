# Ingesting real Sentinel-1/2 via the curated manifest

GeoSentinel does **not** query Copernicus/STAC APIs directly. You download or export tiles **outside** the app, then register them in `curated_manifest.json`.

## Two different files

| File | Purpose |
|------|---------|
| `data/registry/aois.json` | **Where** to monitor (polygons). Max **3** AOIs. |
| `data/registry/curated_manifest.json` | **What imagery** to ingest (list of assets). |

Increasing manifest entries gives **more scenes, dates, and bands** — not new regions unless each asset’s `aoi_id` matches an AOI in `aois.json`.

To monitor a **new region**: add polygon to `aois.json`, then add assets with that `aoi_id` in the manifest.

## What each manifest asset contains

- `id` — unique name (e.g. `s2-levant-20250515-b04`)
- `platform` — `sentinel-1` or `sentinel-2`
- `collection` — `sentinel-2-l2a` or `sentinel-1-grd`
- `aoi_id` — links to `aois.json`
- `datetime` — acquisition time (must fall in 30-day scope when ingesting)
- `bands` — e.g. `["B04"]`, `["B08"]`, `["VV"]`
- `source` — `local` path under `data/` **or** `remote` HTTPS URL
- `checksum_sha256` — required; verified on ingest

Your current manifest has **9 assets**: 6 S2 bands (2 dates × Levant + 1 date × Delta), 3 S1 VV.

## Workflow: Copernicus Data Space Ecosystem (Browser)

1. Open [Copernicus Browser](https://browser.dataspace.copernicus.eu/) (free account).
2. Draw a polygon matching your AOI in `aois.json` (or upload GeoJSON).
3. Select **Sentinel-2 L2A** (or Sentinel-1 GRD).
4. Pick a date with low cloud cover; download/export bands you need:
   - **NDVI pipeline:** B04 + B08 per date (at least 2 dates)
   - **RGB later:** B02, B03, B04 per date
   - **SAR:** VV for 2+ dates
5. Prefer GeoTIFF, clipped to AOI; 512×512 or larger (pipeline clips).
6. Register each file:

```powershell
cd "c:\Users\Sarika Puranik\OneDrive\Desktop\GeoSpatial 3"
python scripts\register_curated_asset.py `
  --file "C:\Downloads\your_B04.tif" `
  --id s2-levant-20250515-b04 `
  --aoi-id aoi-levant `
  --platform sentinel-2 `
  --collection sentinel-2-l2a `
  --datetime 2026-05-15T12:00:00Z `
  --bands B04 `
  --cloud-cover 10
```

7. Repeat per band/date. Then run pipeline:

```powershell
$env:PYTHONPATH="."
$env:DATA_ROOT="$PWD\data"
$env:REGISTRY_PATH="$PWD\data\registry"
python -m backend.pipeline.run_pipeline
```

## Workflow: Microsoft Planetary Computer (STAC)

1. Browse [Planetary Computer](https://planetarycomputer.microsoft.com/catalog/sentinel-2-l2a).
2. Search by bbox/time; open an item’s assets (e.g. `B04` COG href).
3. Either:
   - Download COG → register with `--file`, or
   - Use stable `https://` href + SHA256 → `--remote-url` and `--checksum` in `register_curated_asset.py`.
4. Sign STAC assets if required (PC uses SAS tokens — often easier to **download locally** first).

## Checklist per AOI (minimum useful set)

**Sentinel-2 (×2 dates):** B04, B08 each date  
**Sentinel-1 (×2 dates):** VV each date  

= 8 manifest entries per AOI for full optical + SAR temporal analysis.

## After ingest

- Raw copy: `data/raw/sentinel-2-l2a/{aoi_id}/…`
- Registry STAC items: `data/registry/catalog.json`
- Processed + explainability: run full pipeline
