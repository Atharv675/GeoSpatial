"""
Rule-based explainable anomaly scoring.

No ML — weighted threshold rules with per-signal breakdown for analysts.
"""

from dataclasses import dataclass

import numpy as np

from backend.processing.io import raster_mean_valid
from backend.processing.models import AnomalySignal, AOIAnomalyReport
from backend.shared.config import get_settings
from backend.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SignalInput:
    name: str
    weight: float
    mean_abs: float
    threshold: float
    description: str


def _normalize_component(value: float, threshold: float) -> float:
    if threshold <= 0:
        return 0.0
    return float(min(1.0, value / threshold))


def build_anomaly_signals(inputs: list[SignalInput]) -> list[AnomalySignal]:
    """Build explainable signal list from measurements."""
    signals: list[AnomalySignal] = []
    for inp in inputs:
        triggered = inp.mean_abs >= inp.threshold
        signals.append(
            AnomalySignal(
                signal=inp.name,
                weight=inp.weight,
                value=round(inp.mean_abs, 6),
                threshold=inp.threshold,
                triggered=triggered,
                description=inp.description,
            )
        )
    return signals


def score_aoi_anomaly(
    aoi_id: str,
    datetime_label: str,
    signal_inputs: list[SignalInput],
    evidence_paths: dict[str, str],
    *,
    composite_threshold: float | None = None,
) -> AOIAnomalyReport:
    """
    Compute composite anomaly score from weighted rule-based signals.

    composite = sum(weight * min(1, value/threshold)) / sum(weights)
    """
    settings = get_settings()
    threshold = composite_threshold or settings.anomaly_composite_threshold

    signals = build_anomaly_signals(signal_inputs)
    if not signal_inputs:
        return AOIAnomalyReport(
            aoi_id=aoi_id,
            datetime=datetime_label,
            composite_score=0.0,
            is_anomaly=False,
            signals=signals,
            evidence_paths=evidence_paths,
        )

    weighted = 0.0
    total_weight = sum(s.weight for s in signal_inputs)
    for inp in signal_inputs:
        weighted += inp.weight * _normalize_component(inp.mean_abs, inp.threshold)

    composite = weighted / total_weight if total_weight else 0.0
    any_triggered = any(s.triggered for s in signals)
    is_anomaly = composite >= threshold or (
        any_triggered and composite >= threshold * 0.7
    )

    logger.info(
        "aoi_anomaly_scored",
        aoi_id=aoi_id,
        composite=round(composite, 4),
        is_anomaly=is_anomaly,
    )
    return AOIAnomalyReport(
        aoi_id=aoi_id,
        datetime=datetime_label,
        composite_score=round(composite, 4),
        is_anomaly=is_anomaly,
        signals=signals,
        evidence_paths=evidence_paths,
    )


def build_composite_score_raster(
    rasters: dict[str, np.ndarray],
    weights: dict[str, float],
    thresholds: dict[str, float],
) -> np.ndarray:
    """Pixel-wise composite score from multiple signal rasters (aligned shapes)."""
    if not rasters:
        raise ValueError("No rasters for composite scoring")

    shape = next(iter(rasters.values())).shape
    composite = np.zeros(shape, dtype=np.float32)
    total_w = sum(weights.values())

    for name, arr in rasters.items():
        w = weights.get(name, 0.0)
        th = thresholds.get(name, 1.0)
        if th <= 0:
            continue
        valid = np.isfinite(arr)
        layer = np.zeros(shape, dtype=np.float32)
        layer[valid] = np.clip(np.abs(arr[valid]) / th, 0.0, 1.0)
        composite += (w / total_w) * layer

    return composite
