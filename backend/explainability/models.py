"""Pydantic models for explainability artifacts."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ArtifactType(str, Enum):
    HEATMAP = "heatmap"
    OVERLAY = "overlay"
    BEFORE_AFTER = "before_after"
    CONFIDENCE = "confidence"
    TIMELINE = "timeline"


class ExplainabilityArtifact(BaseModel):
    type: ArtifactType
    aoi_id: str
    name: str
    path: str
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class TimelineEvent(BaseModel):
    datetime: str
    label: str
    category: str
    score: float | None = None
    source: str | None = None


class AOIExplainabilityBundle(BaseModel):
    aoi_id: str
    run_id: str
    artifacts: list[ExplainabilityArtifact] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    confidence_breakdown: dict[str, Any] = Field(default_factory=dict)


class ExplainabilityResult(BaseModel):
    run_id: str
    started_at: datetime
    completed_at: datetime
    bundles: list[AOIExplainabilityBundle]
    artifacts_total: int
    metadata: dict[str, Any] = Field(default_factory=dict)
