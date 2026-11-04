"""Preprocessing API."""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.preprocessing.preprocess import _load_state, run_preprocessing
from backend.shared.exceptions import ValidationError

router = APIRouter(prefix="/preprocessing", tags=["preprocessing"])


class PreprocessRunRequest(BaseModel):
    run_id: str | None = Field(default=None, max_length=64, pattern=r"^[a-zA-Z0-9_-]*$")


@router.get("/status")
async def preprocessing_status() -> dict[str, Any]:
    """Last preprocessing run summary."""
    state = _load_state()
    return {"last_run": state.get("last_run"), "has_run": "last_run" in state}


@router.post("/run", status_code=status.HTTP_200_OK)
async def trigger_preprocessing(body: PreprocessRunRequest | None = None) -> dict[str, Any]:
    """Run raster preprocessing synchronously."""
    run_id = body.run_id if body else None
    try:
        result = run_preprocessing(run_id=run_id)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message)
    return result.model_dump(mode="json")
