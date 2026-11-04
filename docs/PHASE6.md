# Phase 6 — Explainability & Operational Alerts

Phase 6 delivers analyst-facing explainability artifacts and rule-based operational alerts from Phase 4–5 outputs.

## Outputs

All artifacts live under `data/explainability/{aoi_id}/{run_id}/`:

| Subfolder | Contents |
|-----------|----------|
| `heatmaps/` | PNG heatmaps (anomaly score, SAR, temporal indices) |
| `overlays/` | GeoJSON (AOI boundary, anomaly summary, OSINT markers) |
| `before_after/` | Side-by-side PNG comparisons |
| `confidence_breakdown.json` | Merged geospatial + OSINT evidence |
| `timeline.json` | Chronological events |
| `manifest.json` | Full bundle index for frontend/API |

Alerts: `data/alerts/{aoi_id}/alert_{run_id}.json`

## Pipeline

```
generate_alerts → generate_visuals
```

- **generate_alerts**: Reads latest anomaly + correlation reports; writes severity-tagged alerts.
- **generate_visuals**: Builds heatmaps, overlays, before/after, confidence, timeline, manifest.

## API

| Method | Path |
|--------|------|
| GET | `/api/v1/explainability/status` |
| POST | `/api/v1/explainability/run` |
| GET | `/api/v1/explainability/{aoi_id}/manifest` |
| GET | `/api/v1/explainability/{aoi_id}/artifact?path=...` |
| GET | `/api/v1/alerts/status` |
| POST | `/api/v1/alerts/run` |
| GET | `/api/v1/alerts/{aoi_id}` |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `EXPLAINABILITY_PNG_WIDTH` | 512 | Max heatmap PNG width |
| `ALERT_LOW_GEO_THRESHOLD` | 0.25 | Minimum geo score for low alert |
| `ALERT_HIGH_GEO_THRESHOLD` | 0.55 | High severity geo threshold |
| `ALERT_MEDIUM_OSINT_THRESHOLD` | 0.35 | Minimum OSINT fusion for alert |
| `ALERT_CRITICAL_OSINT_THRESHOLD` | 0.65 | Critical when anomaly + high OSINT |

## Dependencies

- `Pillow` + `numpy` for PNG rendering (no ML explainability frameworks)
- Existing `rasterio` stack for GeoTIFF reads

## Phase 7 integration

Frontend loads `manifest.json` per AOI, fetches PNG/GeoJSON via artifact endpoint, and renders timeline + confidence panels.
