# Phase 3 — Raster Processing

## Purpose

Transform ingested Sentinel rasters into analysis-ready products using Rasterio, Rioxarray, and Xarray with deterministic, memory-safe operations.

## Pipeline step

```
preprocess: validate → reproject → clip → cloud mask (S2) → normalize → tile
            → SAR temporal diff (S1 pairs) → temporal xarray stacks
```

## Modules

| Module | Function |
|--------|----------|
| `validate.py` | CRS, dtype, pixel budget checks |
| `reproject.py` | Warp to `TARGET_CRS_EPSG` (default 3857) |
| `clip.py` | AOI polygon clip via `rasterio.mask` |
| `mask.py` | Cloud mask from `eo:cloud_cover` metadata |
| `normalize.py` | Min-max normalization to [0, 1] |
| `tile.py` | 512×512 windowed tiles (chunked reads) |
| `sar_diff.py` | `current - previous` disturbance rasters |
| `stack.py` | Rioxarray + Xarray NetCDF temporal stacks |
| `preprocess.py` | Orchestrator |

## Output layout

```
data/processed/{collection}/{aoi_id}/{item_id}/
  reprojected.tif
  clipped.tif
  masked.tif          # Sentinel-2 only
  cloud_mask.tif
  normalized.tif
  tiles/tile_{row}_{col}.tif

data/processed/sentinel-1-grd/{aoi_id}/disturbance/
  {prev_id}_to_{curr_id}_diff.tif

data/processed/stacks/{aoi_id}/{collection}_temporal.nc
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TARGET_CRS_EPSG` | 3857 | Reprojection target |
| `CLOUD_COVER_THRESHOLD` | 20 | Mask all pixels if above % |
| `TILE_SIZE` | 512 | Output tile dimension |
| `RASTER_CHUNK_SIZE` | 512 | Warp/tile block size |
| `MAX_RASTER_PIXELS` | 16777216 | Safety limit |

## Dependencies

```bash
pip install -r requirements/dev.txt   # includes raster.txt
python scripts/seed_curated_data.py   # writes 512×512 GeoTIFFs
```

## Run

```bash
python -m backend.pipeline.run_pipeline
# or
curl -X POST http://localhost:8000/api/v1/preprocessing/run
```

## API

| Method | Path |
|--------|------|
| GET | `/api/v1/preprocessing/status` |
| POST | `/api/v1/preprocessing/run` |

## Phase 4 integration

Feature engineering reads `normalized.tif`, SAR disturbance rasters, and temporal stacks.
