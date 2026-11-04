"""
Temporal matching for OSINT events vs anomaly dates.
"""

from datetime import datetime, timedelta, timezone


def parse_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def temporal_score(
    event_dt: datetime,
    reference_dt: datetime,
    window_days: int,
) -> float:
    """
    Linear decay score: 1.0 at same day, 0.0 at window edge or beyond.
    """
    if event_dt.tzinfo is None:
        event_dt = event_dt.replace(tzinfo=timezone.utc)
    if reference_dt.tzinfo is None:
        reference_dt = reference_dt.replace(tzinfo=timezone.utc)
    delta = abs((event_dt - reference_dt).total_seconds()) / 86400.0
    if delta > window_days:
        return 0.0
    if window_days == 0:
        return 1.0 if delta < 1 else 0.0
    return max(0.0, 1.0 - (delta / window_days))


def reference_datetime_from_date_key(date_key: str) -> datetime:
    """Parse YYYYMMDD date key to UTC noon reference."""
    return datetime.strptime(date_key, "%Y%m%d").replace(
        hour=12, minute=0, second=0, tzinfo=timezone.utc
    )


def in_time_window(
    event_dt: datetime,
    start: datetime,
    end: datetime,
) -> bool:
    """Check if event falls within inclusive window."""
    if event_dt.tzinfo is None:
        event_dt = event_dt.replace(tzinfo=timezone.utc)
    return start <= event_dt <= end


def window_for_scope(days: int, reference: datetime | None = None) -> tuple[datetime, datetime]:
    """Return (start, end) UTC for project time_range_days scope."""
    ref = reference or datetime.now(timezone.utc)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    return ref - timedelta(days=days), ref
