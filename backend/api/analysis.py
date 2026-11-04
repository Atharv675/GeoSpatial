"""Feature analysis and anomaly API."""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.processing.analyze import _load_state, run_analysis

router = APIRouter(prefix="/analysis", tags=["analysis"])


class AnalysisRunRequest(BaseModel):
    run_id: str | None = Field(default=None, max_length=64, pattern=r"^[a-zA-Z0-9_-]*$")


@router.get("/status")
async def analysis_status() -> dict[str, Any]:
    """Last analysis run summary."""
    state = _load_state()
    return {"last_run": state.get("last_run"), "has_run": "last_run" in state}


@router.post("/run", status_code=status.HTTP_200_OK)
async def trigger_analysis(body: AnalysisRunRequest | None = None) -> dict[str, Any]:
    """Run feature engineering and anomaly scoring."""
    run_id = body.run_id if body else None
    result = run_analysis(run_id=run_id)
    return result.model_dump(mode="json")


@router.get("/anomalies/{aoi_id}")
async def get_aoi_anomalies(aoi_id: str) -> dict[str, Any]:
    """List anomaly reports for an AOI."""
    from backend.shared.config import get_settings
    from backend.shared.security import validate_identifier

    validate_identifier(aoi_id, "aoi_id")
    root = get_settings().resolve_data_path(f"processed/anomalies/{aoi_id}")
    if not root.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No anomalies for AOI")

    reports = []
    for report_file in sorted(root.glob("report_*.json")):
        reports.append(
            {
                "path": str(report_file.relative_to(get_settings().data_root)).replace("\\", "/"),
                "name": report_file.name,
            }
        )
    return {"aoi_id": aoi_id, "reports": reports, "count": len(reports)}
