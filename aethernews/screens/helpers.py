# Created: 2026-08-12
# Last Edited: 2026-08-13 14:28 CT (America/Chicago)
# Path: aethernews/screens/helpers.py
# Purpose: Shared utility functions for screens — date parsing and formatting.

from __future__ import annotations

import datetime
from email import utils as email_utils

RECENT_HOURS = 48
"""Window (hours) for the "recently published" recency band on articles."""


def parse_date(raw: str | None) -> datetime.datetime | None:
    """Parse a feed date string to a UTC-aware datetime, or ``None``.

    Handles both ISO 8601 (Atom) and RFC 2822 (RSS) date formats.
    """
    if not raw:
        return None
    raw = raw.strip()
    parsed: datetime.datetime | None = None
    try:
        parsed = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        pass
    if parsed is None:
        try:
            parsed = email_utils.parsedate_to_datetime(raw)
        except (ValueError, TypeError, LookupError):
            pass
    if parsed is not None and parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed


def format_date(raw: str | None) -> str:
    """Parse a feed date string and return ``YYYY-MM-DD``, or ``"?"`` on failure."""
    dt = parse_date(raw)
    if dt is None:
        return raw[:10] if raw else "?"
    return dt.strftime("%Y-%m-%d")


def is_recent(raw: str | None, hours: int = RECENT_HOURS) -> bool:
    """Return True if *raw* parses and is within *hours* of now (UTC)."""
    dt = parse_date(raw)
    if dt is None:
        return False
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)
    return dt > cutoff


def day_bucket(raw: str | None) -> int:
    """Return a sortable recency bucket for *raw* (larger = older).

    Bucket 0 = today, 1 = yesterday, etc.  Unparseable dates get a large
    bucket so they sink to the bottom.
    """
    dt = parse_date(raw)
    if dt is None:
        return 1_000_000
    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.date()
    day = dt.date()
    return (today - day).days
