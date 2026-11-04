"""Operational alert models (rule-based, no ML)."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OperationalAlert(BaseModel):
    alert_id: str
    aoi_id: str
    severity: AlertSeverity
    title: str
    summary: str
    geospatial_score: float = 0.0
    osint_fusion_score: float = 0.0
    is_anomaly: bool = False
    created_at: datetime
    evidence: dict[str, Any] = Field(default_factory=dict)


class AlertGenerationResult(BaseModel):
    run_id: str
    started_at: datetime
    completed_at: datetime
    alerts: list[OperationalAlert]
    metadata: dict[str, Any] = Field(default_factory=dict)
