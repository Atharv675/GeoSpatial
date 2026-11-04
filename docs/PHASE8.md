# Phase 8 — End-to-End Integration & Deployment

Phase 8 wires the full GeoSentinel stack into a single reproducible Docker Compose deployment with automated data bootstrap and HTTP validation.

## Stack

```
db (PostGIS) → bootstrap (one-shot) → backend (FastAPI) → frontend (nginx + React)
```

| Service | Role |
|---------|------|
| `db` | PostgreSQL 16 + PostGIS 3.4 |
| `bootstrap` | Seeds curated rasters + OSINT demo, runs full pipeline |
| `backend` | API on port 8000 |
| `frontend` | Production build on port 5173 (nginx proxies `/api` → backend) |

## Quick start

```bash
cp .env.example .env
# Set POSTGRES_PASSWORD in .env

docker compose up --build
```

Wait until all services are healthy (first run: bootstrap may take several minutes while the pipeline processes 512×512 tiles).

| URL | Purpose |
|-----|---------|
| http://localhost:5173 | Analyst dashboard (map, timeline, confidence) |
| http://localhost:8000/docs | OpenAPI |
| http://localhost:8000/api/v1/health | Liveness |

## Bootstrap behavior

`scripts/e2e_bootstrap.py`:

1. `init_registry.py`
2. `seed_curated_data.py` — 512×512 GeoTIFFs + manifest
3. `seed_osint_demo.py` — GDELT / FIRMS / ACLED demo events
4. `run_pipeline()` — ingest → … → generate_visuals

On success, writes `data/.e2e_bootstrap_complete`. Subsequent `docker compose up` skips re-seeding unless:

```bash
docker compose run --rm -e FORCE_E2E_BOOTSTRAP=1 bootstrap
```

## Validate deployment

```bash
python scripts/validate_deployment.py
# or
.\scripts\validate_deployment.ps1
```

Checks: health, ready, AOIs, explainability manifest, alerts, OSINT correlations, frontend HTML.

## Local (without Docker)

```bash
pip install -r requirements/dev.txt
set PYTHONPATH=.
python scripts/e2e_bootstrap.py --force
uvicorn backend.main:app --port 8000
cd frontend && npm run dev
python scripts/validate_deployment.py
```

## Dev compose overlay

Hot-reload backend + Vite dev server:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## Tests

```bash
pytest backend/tests/test_e2e_integration.py -q
pytest backend/tests/test_e2e_integration.py -m integration  # full bootstrap (slow)
```

## Environment

| Variable | Description |
|----------|-------------|
| `POSTGRES_PASSWORD` | Required in `.env` for Compose |
| `FORCE_E2E_BOOTSTRAP` | Re-run pipeline on bootstrap container |
| `VITE_API_BASE_URL` | Build-time; default `/api/v1` in production image |

## Troubleshooting

| Issue | Action |
|-------|--------|
| Frontend shows “no explainability” | Run bootstrap or check `data/explainability/aoi-levant/` |
| Bootstrap fails on rasterio | Ensure backend image built with `requirements/dev.txt` |
| Stale data | `FORCE_E2E_BOOTSTRAP=1` + `docker compose run --rm bootstrap` |
| API CORS errors | Add frontend origin to `CORS_ORIGINS` in `.env` |
