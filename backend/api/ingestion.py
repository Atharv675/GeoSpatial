"""Ingestion control and status API."""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.ingestion.ingest import get_last_ingestion_summary, run_ingestion
from backend.ingestion.manifest import load_curated_manifest, filter_assets_by_time_range
from backend.shared.exceptions import ConfigurationError, ValidationError

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


class IngestionRunRequest(BaseModel):
    run_id: str | None = Field(default=None, max_length=64, pattern=r"^[a-zA-Z0-9_-]*$")


@router.get("/manifest")
async def get_manifest_summary() -> dict[str, Any]:
    """Return curated manifest summary (no secrets)."""
    try:
        manifest = load_curated_manifest()
        in_scope = filter_assets_by_time_range(manifest)
    except (ConfigurationError, ValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.message)

    return {
        "version": manifest.version,
        "description": manifest.description,
        "assets_total": len(manifest.assets),
        "assets_in_time_range": len(in_scope),
        "asset_ids": [a.id for a in in_scope],
    }


@router.get("/status")
async def ingestion_status() -> dict[str, Any]:
    """Last ingestion run summary."""
    last = get_last_ingestion_summary()
    return {"last_run": last, "has_run": last is not None}


@router.post("/run", status_code=status.HTTP_200_OK)
async def trigger_ingestion(body: IngestionRunRequest | None = None) -> dict[str, Any]:
    """
    Run curated ingestion synchronously.

    Modular monolith: no background job queue in Phase 2.
    """
    run_id = body.run_id if body else None
    try:
        result = run_ingestion(run_id=run_id)
    except (ConfigurationError, ValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message)

    return result.model_dump(mode="json")
