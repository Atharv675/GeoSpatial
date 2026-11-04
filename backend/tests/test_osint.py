"""Phase 5 OSINT correlation tests."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.osint.correlate import run_correlation
from backend.osint.keywords import extract_keywords_from_anomaly_report, keyword_match_score
from backend.osint.models import OsintEvent, OsintSource
from backend.osint.scoring import correlate_event, fusion_confidence
from backend.osint.spatial import point_in_polygon, spatial_score_for_point
from backend.osint.temporal import temporal_score
from backend.shared.config import get_settings


def _clear_caches() -> None:
    get_settings.cache_clear()


@pytest.fixture
def osint_env(tmp_path: Path, monkeypatch):
    data = tmp_path / "data"
    registry = data / "registry"
    registry.mkdir(parents=True)
    aois_src = Path(__file__).resolve().parents[2] / "data" / "registry" / "aois.json"
    (registry / "aois.json").write_text(aois_src.read_text(encoding="utf-8"), encoding="utf-8")

    now = datetime.now(timezone.utc)
    date_key = now.strftime("%Y%m%d")

    # Anomaly report (Phase 4 shape)
    report = {
        "aoi_id": "aoi-levant",
        "datetime": date_key,
        "composite_score": 0.62,
        "is_anomaly": True,
        "signals": [
            {
                "signal": "vegetation_change",
                "weight": 0.35,
                "value": 0.4,
                "threshold": 0.15,
                "triggered": True,
                "description": "veg",
            },
            {
                "signal": "burn_anomaly",
                "weight": 0.2,
                "value": 0.3,
                "threshold": 0.18,
                "triggered": True,
                "description": "burn",
            },
        ],
        "keywords_used": [],
        "matches": [],
        "fusion_confidence": 0.0,
        "sources_agreeing": [],
    }
    anom_dir = data / "processed" / "anomalies" / "aoi-levant"
    anom_dir.mkdir(parents=True)
    (anom_dir / f"report_{date_key}.json").write_text(json.dumps(report), encoding="utf-8")

    # Curated OSINT inside AOI
    gdelt_events = [
        {
            "event_id": "test-gdelt-1",
            "source": "gdelt",
            "title": "Wildfire vegetation burn near coast",
            "summary": "fire wildfire smoke",
            "datetime": now.isoformat(),
            "latitude": 31.25,
            "longitude": 34.80,
            "keywords": ["wildfire", "burn", "vegetation"],
            "raw": {},
        }
    ]
    firms_events = [
        {
            "event_id": "test-firms-1",
            "source": "firms",
            "title": "Active fire detection",
            "summary": "fire hotspot",
            "datetime": now.isoformat(),
            "latitude": 31.24,
            "longitude": 34.79,
            "keywords": ["fire", "wildfire"],
            "raw": {},
        }
    ]
    for source, events in [("gdelt", gdelt_events), ("firms", firms_events), ("acled", [])]:
        out = data / "raw" / "osint" / source
        out.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"events": events, "count": len(events)})
        (out / "events.json").write_text(payload, encoding="utf-8")
        (out / "events_curated.json").write_text(payload, encoding="utf-8")

    monkeypatch.setenv("DATA_ROOT", str(data))
    monkeypatch.setenv("REGISTRY_PATH", str(registry))
    monkeypatch.setenv("OSINT_LIVE_FETCH_ENABLED", "false")
    _clear_caches()
    yield data
    _clear_caches()


def test_point_in_polygon():
    ring = [[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]
    assert point_in_polygon(1, 1, ring)
    assert not point_in_polygon(5, 5, ring)


def test_keyword_extraction():
    report = {
        "is_anomaly": True,
        "signals": [{"signal": "burn_anomaly", "triggered": True}],
    }
    kws = extract_keywords_from_anomaly_report(report)
    assert "fire" in kws or "burn" in kws


def test_correlate_event_scores():
    aoi_geom = {
        "type": "Polygon",
        "coordinates": [[[34.75, 31.2], [34.85, 31.2], [34.85, 31.3], [34.75, 31.3], [34.75, 31.2]]],
    }
    bbox = [34.75, 31.2, 34.85, 31.3]
    event = OsintEvent(
        event_id="e1",
        source=OsintSource.GDELT,
        title="wildfire burn vegetation",
        summary="fire",
        datetime=datetime.now(timezone.utc),
        latitude=31.25,
        longitude=34.80,
        keywords=["fire", "burn"],
    )
    match = correlate_event(event, ["fire", "burn"], aoi_geom, bbox, datetime.now(timezone.utc))
    assert match is not None
    assert match.confidence >= 0.35


def test_run_correlation(osint_env):
    result = run_correlation(run_id="test-osint")
    assert result.total_matches >= 1
    assert len(result.reports) >= 1
    levant = next((r for r in result.reports if r.aoi_id == "aoi-levant"), None)
    assert levant is not None
    assert levant.fusion_confidence > 0
    assert len(levant.sources_agreeing) >= 1

    settings = get_settings()
    out = settings.resolve_data_path("processed/osint/correlations/aoi-levant/correlation_test-osint.json")
    assert out.exists()


@pytest.mark.anyio
async def test_api_osint_run(client, osint_env):
    _clear_caches()
    r = await client.post("/api/v1/osint/run", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["total_matches"] >= 0
    assert "ingest_results" in body


@pytest.mark.anyio
async def test_api_osint_events(client, osint_env):
    r = await client.get("/api/v1/osint/events")
    assert r.status_code == 200
    assert "sources" in r.json()
