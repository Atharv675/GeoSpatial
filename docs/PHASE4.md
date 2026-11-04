# Phase 4 — Feature Engineering & Anomaly Engine

## Purpose

Compute spectral indices, temporal changes, SAR disturbance integration, and **rule-based explainable** anomaly scores.

No ML — deterministic, analyst-readable outputs.

## Pipeline step

```
analyze:
  NDVI / NDWI / NBR  →  temporal differencing  →  SAR disturbance maps
  →  weighted rule-based anomaly scoring  →  JSON reports + score rasters
```

## Modules

| Module | Role |
|--------|------|
| `indices.py` | NDVI, NDWI, NBR |
| `bands.py` | Pair curated bands by AOI + date |
| `temporal.py` | Current − previous feature diffs |
| `sar_features.py` | Phase 3 SAR disturbance registration |
| `scoring.py` | Weighted threshold anomaly rules |
| `analyze.py` | Orchestrator |

## Outputs

```
data/processed/features/{aoi_id}/{YYYYMMDD}/
  ndvi.tif, ndwi.tif, nbr.tif

data/processed/features/{aoi_id}/temporal/
  ndvi_{prev}_to_{curr}_diff.tif

data/processed/features/{aoi_id}/sar/
  *_diff.tif

data/processed/anomalies/{aoi_id}/
  anomaly_score_{date}.tif
  report_{date}.json   # explainable signal breakdown
```

## Scoring rules (configurable)

| Signal | Default threshold | Weight |
|--------|-------------------|--------|
| Vegetation (temporal NDVI) | 0.15 | 0.35 |
| Water (temporal NDWI) | 0.12 | 0.25 |
| Burn (temporal NBR) | 0.18 | 0.20 |
| SAR surface disturbance | 0.20 | 0.20 |
| Composite anomaly | 0.45 | — |

## API

| Method | Path |
|--------|------|
| POST | `/api/v1/analysis/run` |
| GET | `/api/v1/analysis/status` |
| GET | `/api/v1/analysis/anomalies/{aoi_id}` |

## Run

Requires Phase 3 `normalized.tif` outputs:

```bash
python -m backend.pipeline.run_pipeline
# or
curl -X POST http://localhost:8000/api/v1/analysis/run
```

## Curated band pairing

Seed data includes paired B04+B08 per acquisition for NDVI/NDWI. NBR uses NIR+SWIR or NIR+RED proxy when SWIR absent (documented in feature metadata).

## Phase 5 integration

OSINT correlation reads `report_{date}.json` anomaly flags per AOI.
