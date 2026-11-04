# GeoSentinel

**Geospatial intelligence and OSINT fusion platform** for explainable temporal anomaly detection and regional situational awareness.

GeoSentinel combines Sentinel-1 SAR, Sentinel-2 optical imagery, temporal raster analysis, rule-based OSINT correlation, and operational explainability — without military target identification, autonomous surveillance, or geopolitical ML prediction.

## Architecture

- **Modular monolith** (Python FastAPI + React/Leaflet)
- **Deterministic pipeline** — explicit step order, no distributed workers
- **PostgreSQL + PostGIS** for spatial persistence
- **Lightweight metadata registry** — STAC-compatible JSON structure; **designed for future STAC migration**
- **Docker Compose** deployment

## Project scope (strict)

| Limit | Value |
|-------|-------|
| AOIs | 2–3 |
| Time range | 30 days |
| Update frequency | Weekly |
| Tile size | 512×512 |
| Imagery | Curated only |

## Repository layout

```
backend/     API, ingestion, processing, OSINT, pipeline, storage, tests
frontend/    React + Leaflet dashboard
data/        raw, processed, explainability, alerts, registry
scripts/     Utilities and pipeline helpers
docs/        Architecture and phase documentation
infrastructure/  Docker, database init
requirements/  Pinned Python dependencies
```

## Technology stack

| Layer | Stack |
|-------|-------|
| Backend | Python, FastAPI, SQLAlchemy, asyncpg |
| Database | PostgreSQL 16, PostGIS 3.4 |
| Raster (Phase 3+) | Rasterio, Rioxarray, Xarray |
| Frontend | React 18, Leaflet, GeoJSON |
| OSINT (Phase 5+) | GDELT, FIRMS, ACLED |
| Deploy | Docker, Docker Compose |

## Quick start

### 1. Environment

```bash
cp .env.example .env
# Edit POSTGRES_PASSWORD and other values — never commit .env
```

### 2. Docker (recommended — full E2E, Phase 8)

```bash
docker compose up --build
```

First start runs the **bootstrap** service (seed + full pipeline), then serves the analyst dashboard.

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:5173 |
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |

```bash
python scripts/validate_deployment.py
# Re-run pipeline seed: docker compose run --rm -e FORCE_E2E_BOOTSTRAP=1 bootstrap
```

See [docs/PHASE8.md](docs/PHASE8.md).

### 3. Local development (backend)

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements/dev.txt
set PYTHONPATH=.
pytest backend/tests -q
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Local development (frontend)

```bash
cd frontend
npm install
npm run dev
```

## Pipeline (deterministic)

```
run_pipeline.py → ingest → preprocess → analyze → correlate_osint → generate_alerts → generate_visuals
```

All pipeline steps are implemented. For a one-shot local demo:

```bash
python scripts/e2e_bootstrap.py --force
python -m backend.pipeline.run_pipeline   # or use bootstrap only
```

### Ingestion (Phase 2)

```bash
python scripts/seed_curated_data.py
curl -X POST http://localhost:8000/api/v1/ingestion/run
curl http://localhost:8000/api/v1/aois
```

See [docs/PHASE2.md](docs/PHASE2.md).

### Preprocessing (Phase 3)

```bash
pip install -r requirements/dev.txt
python scripts/seed_curated_data.py
curl -X POST http://localhost:8000/api/v1/preprocessing/run
```

See [docs/PHASE3.md](docs/PHASE3.md).

### Analysis (Phase 4)

```bash
curl -X POST http://localhost:8000/api/v1/analysis/run
curl http://localhost:8000/api/v1/analysis/anomalies/aoi-levant
```

See [docs/PHASE4.md](docs/PHASE4.md).

### OSINT correlation (Phase 5)

```bash
python scripts/seed_osint_demo.py
curl -X POST http://localhost:8000/api/v1/osint/run
curl http://localhost:8000/api/v1/osint/correlations/aoi-levant
```

See [docs/PHASE5.md](docs/PHASE5.md).

## API (Phase 1)

| Endpoint | Description |
|----------|-------------|
| `GET /` | Service info |
| `GET /api/v1/health` | Liveness |
| `GET /api/v1/ready` | Readiness (DB + registry) |
| `GET /api/v1/registry/items` | List STAC-compatible items |
| `POST /api/v1/registry/items` | Register curated item |
| `GET /api/v1/aois` | List AOIs (GeoJSON) |
| `POST /api/v1/ingestion/run` | Run curated ingestion |
| `GET /api/v1/ingestion/status` | Last ingestion run |
| `POST /api/v1/preprocessing/run` | Run raster preprocessing |
| `GET /api/v1/preprocessing/status` | Last preprocess run |
| `POST /api/v1/analysis/run` | Feature engineering + anomalies |
| `GET /api/v1/analysis/anomalies/{aoi_id}` | Explainable anomaly reports |
| `POST /api/v1/osint/run` | OSINT ingest + correlation |
| `GET /api/v1/osint/correlations/{aoi_id}` | Fusion reports per AOI |
| `GET /api/v1/explainability/{aoi_id}/manifest` | Explainability bundle |
| `GET /api/v1/explainability/{aoi_id}/artifact` | PNG / GeoJSON artifacts |
| `GET /api/v1/alerts/{aoi_id}` | Operational alerts per AOI |

## Security

- Secrets via environment variables only
- Path traversal protection on data paths
- Parameterized DB access via SQLAlchemy
- Non-root Docker containers
- Input validation on registry and GeoJSON types
- No stack traces exposed in production responses

## Implementation phases

| Phase | Status | Focus |
|-------|--------|-------|
| 1 | ✅ Foundation | Docker, FastAPI, PostGIS, registry, frontend skeleton |
| 2 | ✅ Ingestion | Sentinel-1/2 curated ingest, AOIs, resumable downloads |
| 3 | ✅ Raster processing | Reproject, clip, mask, tile, SAR diff, xarray stacks |
| 4 | ✅ Anomaly engine | NDVI, NDWI, NBR, temporal diff, explainable scoring |
| 5 | ✅ OSINT fusion | GDELT, FIRMS, ACLED, rule-based correlation |
| 6 | ✅ Explainability | Heatmaps, overlays, before/after, confidence, timelines, alerts |
| 7 | ✅ Frontend | Map overlays, timeline, confidence panel, explainability gallery |
| 8 | ✅ E2E deploy | Docker Compose bootstrap, nginx frontend, validation |

See [docs/PHASE1.md](docs/PHASE1.md) for Phase 1 details. Phase 6: [docs/PHASE6.md](docs/PHASE6.md). Phase 7: [docs/PHASE7.md](docs/PHASE7.md). Phase 8: [docs/PHASE8.md](docs/PHASE8.md).

## License

Use and extend per your project requirements.
