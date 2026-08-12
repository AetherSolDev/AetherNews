# Created: 2026-08-12
# Last Edited: 2026-08-12 17:40 CT (America/Chicago)
# Path: aethernews/screens/helpers.py
# Purpose: Shared utility functions for screens — date formatting.

from __future__ import annotations

import datetime
from email import utils as email_utils


def format_date(raw: str | None) -> str:
    """Parse a feed date string and return ``YYYY-MM-DD``, or ``"?"`` on failure.

    Handles both ISO 8601 (Atom) and RFC 2822 (RSS) date formats.
    """
    if not raw:
        return "?"
    raw = raw.strip()
    try:
        dt = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        pass
    try:
        dt = email_utils.parsedate_to_datetime(raw)
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError, LookupError):
        pass
    return raw[:10]
