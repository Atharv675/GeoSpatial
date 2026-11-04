"""Pydantic models for OSINT events and correlation results."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class OsintSource(str, Enum):
    GDELT = "gdelt"
    FIRMS = "firms"
    ACLED = "acled"


class OsintEvent(BaseModel):
    """Normalized OSINT event from any feed."""

    event_id: str
    source: OsintSource
    title: str = ""
    summary: str = ""
    datetime: datetime
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    keywords: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class CorrelationMatch(BaseModel):
    """Single OSINT event matched to a geospatial anomaly."""

    event_id: str
    source: OsintSource
    confidence: float = Field(ge=0.0, le=1.0)
    spatial_score: float
    temporal_score: float
    keyword_score: float
    matched_keywords: list[str] = Field(default_factory=list)
    title: str = ""
    datetime: str = ""
    explanation: str = ""


class AOICorrelationReport(BaseModel):
    aoi_id: str
    anomaly_date: str
    anomaly_composite_score: float
    anomaly_is_triggered: bool
    keywords_used: list[str]
    matches: list[CorrelationMatch]
    fusion_confidence: float = Field(ge=0.0, le=1.0)
    sources_agreeing: list[str] = Field(default_factory=list)


class OsintIngestResult(BaseModel):
    source: OsintSource
    events_count: int
    status: str
    message: str | None = None
    storage_path: str | None = None


class CorrelationResult(BaseModel):
    run_id: str
    started_at: datetime
    completed_at: datetime
    ingest_results: list[OsintIngestResult]
    reports: list[AOICorrelationReport]
    total_matches: int
    metadata: dict[str, Any] = Field(default_factory=dict)
