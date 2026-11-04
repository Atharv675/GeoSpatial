"""Explainability and alert API."""

import json
from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.alerts.generate import generate_alerts, get_last_alerts
from backend.explainability.generate import get_last_explainability, run_explainability
from backend.shared.config import get_settings
from backend.shared.security import safe_resolve_under, validate_identifier

router = APIRouter(tags=["explainability"])


class RunRequest(BaseModel):
    run_id: str | None = Field(default=None, max_length=64, pattern=r"^[a-zA-Z0-9_-]*$")


@router.get("/explainability/status")
async def explainability_status() -> dict[str, Any]:
    last = get_last_explainability()
    return {"last_run": last, "has_run": last is not None}


@router.post("/explainability/run", status_code=status.HTTP_200_OK)
async def trigger_explainability(body: RunRequest | None = None) -> dict[str, Any]:
    run_id = body.run_id if body else None
    result = run_explainability(run_id=run_id)
    return result.model_dump(mode="json")


@router.get("/explainability/{aoi_id}/manifest")
async def get_aoi_manifest(aoi_id: str, run_id: str | None = None) -> dict[str, Any]:
    validate_identifier(aoi_id, "aoi_id")
    settings = get_settings()
    root = settings.resolve_data_path(f"explainability/{aoi_id}")
    if not root.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No explainability data")

    if run_id:
        validate_identifier(run_id, "run_id")
        path = root / run_id / "manifest.json"
    else:
        runs = sorted([d for d in root.iterdir() if d.is_dir()], key=lambda p: p.name)
        if not runs:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No runs found")
        path = runs[-1] / "manifest.json"

    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manifest not found")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/explainability/{aoi_id}/artifact")
async def get_artifact(aoi_id: str, path: str) -> FileResponse:
    """Serve a single explainability artifact (PNG or GeoJSON) by relative path."""
    validate_identifier(aoi_id, "aoi_id")
    settings = get_settings()
    if not path.startswith(f"explainability/{aoi_id}/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid artifact path")
    full = safe_resolve_under(settings.data_root, path)
    if not full.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    media = "image/png" if full.suffix.lower() == ".png" else "application/geo+json"
    if full.suffix.lower() == ".json":
        media = "application/json"
    return FileResponse(full, media_type=media)


@router.get("/alerts/status")
async def alerts_status() -> dict[str, Any]:
    last = get_last_alerts()
    return {"last_run": last, "has_run": last is not None}


@router.post("/alerts/run", status_code=status.HTTP_200_OK)
async def trigger_alerts(body: RunRequest | None = None) -> dict[str, Any]:
    run_id = body.run_id if body else None
    result = generate_alerts(run_id=run_id)
    return result.model_dump(mode="json")


@router.get("/alerts/{aoi_id}")
async def list_aoi_alerts(aoi_id: str) -> dict[str, Any]:
    validate_identifier(aoi_id, "aoi_id")
    root = get_settings().resolve_data_path(f"alerts/{aoi_id}")
    if not root.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No alerts for AOI")
    files = [
        {
            "name": f.name,
            "path": str(f.relative_to(get_settings().data_root)).replace("\\", "/"),
        }
        for f in sorted(root.glob("alert_*.json"))
    ]
    return {"aoi_id": aoi_id, "alerts": files, "count": len(files)}
