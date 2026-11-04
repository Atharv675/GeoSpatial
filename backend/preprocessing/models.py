"""Pydantic models for raster preprocessing results."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PreprocessStatus(str, Enum):
    OK = "ok"
    SKIPPED = "skipped"
    FAILED = "failed"


class ItemPreprocessResult(BaseModel):
    item_id: str
    status: PreprocessStatus
    message: str | None = None
    outputs: dict[str, str] = Field(default_factory=dict)


class SarDiffResult(BaseModel):
    aoi_id: str
    previous_item_id: str
    current_item_id: str
    status: PreprocessStatus
    output_path: str | None = None
    message: str | None = None


class StackResult(BaseModel):
    aoi_id: str
    collection: str
    status: PreprocessStatus
    output_path: str | None = None
    time_steps: int = 0
    message: str | None = None


class PreprocessResult(BaseModel):
    run_id: str
    started_at: datetime
    completed_at: datetime
    items_total: int
    items_ok: int
    items_failed: int
    item_results: list[ItemPreprocessResult]
    sar_diffs: list[SarDiffResult] = Field(default_factory=list)
    stacks: list[StackResult] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
