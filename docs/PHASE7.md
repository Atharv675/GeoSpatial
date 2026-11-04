# Phase 7 — Frontend Analyst Dashboard

Phase 7 connects the React/Leaflet UI to Phase 6 explainability outputs and existing AOI/OSINT APIs.

## Features

| Feature | Description |
|---------|-------------|
| **AOI selector** | Loads active AOIs from `GET /api/v1/aois` |
| **Map overlays** | GeoJSON layers: boundary, anomaly summary (choropleth), OSINT point markers |
| **Layer toggles** | Show/hide each overlay independently |
| **Confidence panel** | Merged geospatial + OSINT breakdown from manifest |
| **Timeline** | Filterable event list (all / anomaly / signal / osint) |
| **Visual gallery** | Heatmap and before/after PNGs via artifact URL |
| **Alerts** | Latest operational alert per AOI from `GET /api/v1/alerts/status` |

## Data flow

```
GET /aois → select AOI
GET /explainability/{aoi_id}/manifest → bundle + timeline + confidence
GET /explainability/{aoi_id}/artifact?path=... → GeoJSON overlays + PNG images
GET /alerts/status → severity badge in confidence panel
```

## Run locally

```bash
# Terminal 1 — API (with data from pipeline / seed scripts)
cd backend
PYTHONPATH=. uvicorn backend.main:app --reload --port 8000

# Terminal 2 — frontend (proxies /api → :8000)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Ensure `generate_visuals` has run so manifests exist under `data/explainability/`.

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `/api/v1` | API prefix (use full URL if not using Vite proxy) |
| `VITE_API_PROXY` | `http://localhost:8000` | Vite dev proxy target |

## Source layout

```
frontend/src/
  api/          client + types
  hooks/        useExplainability
  overlays/     MapOverlays, mapStyles
  maps/         MapView, FitBounds, geoUtils
  components/   AOI, layers, timeline, confidence, gallery
  pages/        DashboardPage
```

## Phase 8

End-to-end Docker Compose validation: API + frontend + seeded explainability bundle in one `docker compose up`.
