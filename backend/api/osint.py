"""OSINT correlation API."""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.osint.correlate import get_last_correlation_summary, run_correlation
from backend.shared.config import get_settings
from backend.shared.security import validate_identifier

router = APIRouter(prefix="/osint", tags=["osint"])


class OsintRunRequest(BaseModel):
    run_id: str | None = Field(default=None, max_length=64, pattern=r"^[a-zA-Z0-9_-]*$")


@router.get("/status")
async def osint_status() -> dict[str, Any]:
    """Last OSINT correlation run summary."""
    last = get_last_correlation_summary()
    return {"last_run": last, "has_run": last is not None}


@router.post("/run", status_code=status.HTTP_200_OK)
async def trigger_osint_correlation(body: OsintRunRequest | None = None) -> dict[str, Any]:
    """Run OSINT ingestion and correlation with anomaly reports."""
    run_id = body.run_id if body else None
    result = run_correlation(run_id=run_id)
    return result.model_dump(mode="json")


@router.get("/correlations/{aoi_id}")
async def get_aoi_correlations(aoi_id: str) -> dict[str, Any]:
    """List correlation reports for an AOI."""
    validate_identifier(aoi_id, "aoi_id")
    root = get_settings().resolve_data_path(f"processed/osint/correlations/{aoi_id}")
    if not root.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No correlations found")

    files = []
    for f in sorted(root.glob("correlation_*.json")):
        files.append(
            {
                "name": f.name,
                "path": str(f.relative_to(get_settings().data_root)).replace("\\", "/"),
            }
        )
    return {"aoi_id": aoi_id, "correlations": files, "count": len(files)}


@router.get("/events")
async def list_osint_events() -> dict[str, Any]:
    """Summary of ingested OSINT events by source (no secrets)."""
    import json

    settings = get_settings()
    summary = {}
    for source in ("gdelt", "firms", "acled"):
        path = settings.resolve_data_path(f"raw/osint/{source}/events.json")
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            summary[source] = data.get("count", 0)
        else:
            summary[source] = 0
    return {"sources": summary, "total": sum(summary.values())}
