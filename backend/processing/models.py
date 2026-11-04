"""Pydantic models for feature engineering and anomaly detection."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AnalysisStatus(str, Enum):
    OK = "ok"
    SKIPPED = "skipped"
    FAILED = "failed"


class FeatureResult(BaseModel):
    feature: str
    aoi_id: str
    status: AnalysisStatus
    output_path: str | None = None
    message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnomalySignal(BaseModel):
    """Explainable signal contributing to anomaly score."""

    signal: str
    weight: float
    value: float
    threshold: float
    triggered: bool
    description: str


class AOIAnomalyReport(BaseModel):
    aoi_id: str
    datetime: str
    composite_score: float
    is_anomaly: bool
    signals: list[AnomalySignal]
    evidence_paths: dict[str, str] = Field(default_factory=dict)


class AnalysisResult(BaseModel):
    run_id: str
    started_at: datetime
    completed_at: datetime
    features_ok: int
    features_failed: int
    anomalies_detected: int
    feature_results: list[FeatureResult]
    reports: list[AOIAnomalyReport]
    metadata: dict[str, Any] = Field(default_factory=dict)
