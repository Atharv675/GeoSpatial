# Phase 1 — Foundation

## Purpose

Establish a stable, secure, deployable base for GeoSentinel without implementing ingestion or raster processing yet.

## Delivered components

### Backend (`backend/`)

- **FastAPI** application factory (`main.py`)
- **Centralized config** (`shared/config.py`) — scope limits enforced via Pydantic
- **Structured logging** (`shared/logging.py`) — structlog, JSON in production
- **Security utilities** (`shared/security.py`) — path sanitization, identifier validation
- **PostgreSQL + PostGIS** models (`storage/models.py`) and async sessions (`storage/database.py`)
- **Metadata registry** (`storage/registry.py`) — STAC-shaped JSON catalog
- **API routes** — health, readiness, registry CRUD
- **Pipeline stub** (`pipeline/run_pipeline.py`) — deterministic step list

### Frontend (`frontend/`)

- Vite + React 18 + TypeScript
- Leaflet map with placeholder AOI GeoJSON
- API client for health/ready endpoints
- Sidebar status panel

### Infrastructure

- `docker-compose.yml` — db, backend, frontend
- Non-root Dockerfiles
- PostGIS `init.sql`

### Data

- `data/registry/catalog.json` — empty items array, collection definitions
- Directory structure for raw/processed/explainability/alerts

### Tests (`backend/tests/`)

- Configuration and security unit tests
- Health API integration tests
- Registry read/write tests

## Integration points for Phase 2+

| Module | Phase 1 hook |
|--------|----------------|
| `backend/ingestion/` | Package reserved; pipeline step `ingest` |
| `backend/preprocessing/` | Step `preprocess` |
| `backend/processing/` | Step `analyze` |
| `backend/osint/` | Step `correlate_osint` |
| `backend/alerts/` | Step `generate_alerts` |
| `backend/explainability/` | Step `generate_visuals` |
| Registry | `register_item()` for curated Sentinel assets |
| AOI table | PostGIS `aois` ready for AOI config import |

## Running tests

```bash
pip install -r requirements/dev.txt
set PYTHONPATH=.
pytest backend/tests -v
```

## Verification checklist

- [ ] `pytest` passes
- [ ] `docker compose up --build` starts all services
- [ ] `GET /api/v1/health` returns `ok`
- [ ] Frontend loads map at http://localhost:5173
- [ ] Registry catalog exists at `data/registry/catalog.json`
