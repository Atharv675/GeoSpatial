"""
Rule-based keyword extraction for OSINT queries.

Maps anomaly signal types to search keyword sets — no NLP/ML.
"""

from typing import Any

# Signal name -> OSINT search keywords
SIGNAL_KEYWORDS: dict[str, list[str]] = {
    "vegetation_change": ["vegetation", "drought", "agriculture", "crop"],
    "water_change": ["flood", "water", "rainfall", "inundation"],
    "burn_anomaly": ["fire", "wildfire", "burn", "smoke"],
    "surface_disturbance": ["construction", "disturbance", "activity", "infrastructure"],
    "optical_change": ["land", "change", "development"],
}

BASELINE_KEYWORDS = ["conflict", "unrest", "environment"]


def extract_keywords_from_anomaly_report(report: dict[str, Any]) -> list[str]:
    """
    Extract deduplicated keywords from Phase 4 anomaly report JSON.

    Uses triggered signals only; adds baseline context keywords.
    """
    keywords: set[str] = set()
    for signal in report.get("signals", []):
        if not signal.get("triggered"):
            continue
        name = signal.get("signal", "")
        for kw in SIGNAL_KEYWORDS.get(name, []):
            keywords.add(kw.lower())
    if report.get("is_anomaly"):
        keywords.update(BASELINE_KEYWORDS)
    if not keywords:
        keywords.update(BASELINE_KEYWORDS[:2])
    return sorted(keywords)


def keyword_match_score(event_keywords: list[str], query_keywords: list[str]) -> tuple[float, list[str]]:
    """
    Fraction of query keywords found in event text/keywords.

    Returns (score 0-1, matched list).
    """
    if not query_keywords:
        return 0.0, []
    event_set = {k.lower() for k in event_keywords}
    event_text = " ".join(event_keywords).lower()
    matched = []
    for q in query_keywords:
        ql = q.lower()
        if ql in event_set or ql in event_text:
            matched.append(q)
    score = len(matched) / len(query_keywords) if query_keywords else 0.0
    return min(1.0, score), matched
