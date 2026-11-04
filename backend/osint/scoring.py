"""
Rule-based OSINT–anomaly fusion confidence scoring.

Weights: spatial 0.40, temporal 0.35, keyword 0.25
Multi-source agreement bonus (capped).
"""

from backend.osint.keywords import keyword_match_score
from backend.osint.models import CorrelationMatch, OsintEvent
from backend.osint.spatial import spatial_score_for_point
from backend.osint.temporal import parse_datetime, temporal_score
from backend.shared.config import get_settings

SPATIAL_W = 0.40
TEMPORAL_W = 0.35
KEYWORD_W = 0.25
MIN_MATCH_CONFIDENCE = 0.35


def correlate_event(
    event: OsintEvent,
    query_keywords: list[str],
    aoi_geometry: dict,
    aoi_bbox: list[float],
    reference_dt,
) -> CorrelationMatch | None:
    """Score single OSINT event against anomaly context."""
    settings = get_settings()
    sp = spatial_score_for_point(
        event.longitude, event.latitude, aoi_geometry, aoi_bbox
    )
    if sp <= 0:
        return None

    tp = temporal_score(
        parse_datetime(event.datetime),
        parse_datetime(reference_dt),
        settings.osint_correlation_window_days,
    )
    if tp <= 0:
        return None

    event_kws = event.keywords + event.title.lower().split() + event.summary.lower().split()
    kw_score, matched = keyword_match_score(event_kws, query_keywords)
    if kw_score <= 0 and sp < 1.0:
        return None

    confidence = SPATIAL_W * sp + TEMPORAL_W * tp + KEYWORD_W * kw_score
    if confidence < MIN_MATCH_CONFIDENCE:
        return None

    explanation = (
        f"spatial={sp:.2f} temporal={tp:.2f} keyword={kw_score:.2f} "
        f"matched={','.join(matched[:5])}"
    )
    return CorrelationMatch(
        event_id=event.event_id,
        source=event.source,
        confidence=round(min(0.99, confidence), 4),
        spatial_score=round(sp, 4),
        temporal_score=round(tp, 4),
        keyword_score=round(kw_score, 4),
        matched_keywords=matched,
        title=event.title[:200],
        datetime=parse_datetime(event.datetime).isoformat(),
        explanation=explanation,
    )


def fusion_confidence(matches: list[CorrelationMatch]) -> tuple[float, list[str]]:
    """
    Aggregate fusion score with multi-source agreement bonus.

    Returns (fusion_confidence, sources_agreeing).
    """
    if not matches:
        return 0.0, []
    top = max(m.confidence for m in matches)
    sources = sorted({m.source.value for m in matches})
    bonus = min(0.15, 0.05 * max(0, len(sources) - 1))
    return round(min(0.99, top + bonus), 4), sources
