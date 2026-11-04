# Phase 5 — OSINT Correlation

## Purpose

Fuse open-source intelligence (GDELT, FIRMS, ACLED) with Phase 4 geospatial anomalies using **rule-based** spatial, temporal, and keyword matching.

No AI geopolitical reasoning.

## Pipeline step

```
correlate_osint:
  ingest GDELT / FIRMS / ACLED  →  normalize events
  →  match to AOI anomalies (spatial + temporal + keywords)
  →  fusion confidence score + multi-source agreement
```

## Modules

| Module | Role |
|--------|------|
| `gdelt.py` | GDELT DOC API (HTTPS) + curated fallback |
| `firms.py` | NASA FIRMS CSV (requires `FIRMS_MAP_KEY`) |
| `acled.py` | ACLED API (requires `ACLED_EMAIL` / `ACLED_PASSWORD`) |
| `keywords.py` | Keyword extraction from anomaly signals |
| `spatial.py` | Point-in-polygon + bbox scoring |
| `temporal.py` | Time window decay scoring |
| `scoring.py` | Weighted fusion confidence |
| `correlate.py` | Orchestrator |

## Confidence formula (rule-based)

```
confidence = 0.40 × spatial + 0.35 × temporal + 0.25 × keyword
fusion = top_match + min(0.15, 0.05 × (num_sources - 1))
```

Minimum match confidence: 0.35

## Outputs

```
data/raw/osint/{gdelt,firms,acled}/events.json
data/processed/osint/correlations/{aoi_id}/correlation_{run_id}.json
data/processed/osint/correlation_state.json
```

## Offline demo data

```bash
python scripts/seed_osint_demo.py
```

Set `OSINT_LIVE_FETCH_ENABLED=true` and API keys in `.env` for live feeds.

## API

| Method | Path |
|--------|------|
| POST | `/api/v1/osint/run` |
| GET | `/api/v1/osint/status` |
| GET | `/api/v1/osint/events` |
| GET | `/api/v1/osint/correlations/{aoi_id}` |

## Environment

| Variable | Description |
|----------|-------------|
| `OSINT_LIVE_FETCH_ENABLED` | `false` = curated only (default) |
| `OSINT_CORRELATION_WINDOW_DAYS` | Temporal match window (default 7) |
| `FIRMS_MAP_KEY` | NASA FIRMS API key |
| `ACLED_EMAIL` / `ACLED_PASSWORD` | ACLED credentials |

## Phase 6 integration

Explainability layer reads `correlation_{run_id}.json` for analyst-facing fusion summaries.
