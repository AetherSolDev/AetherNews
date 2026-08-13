# Created: 2026-08-13
# Last Edited: 2026-08-13 14:29 CT (America/Chicago)
# Path: tests/unit/test_helpers.py
# Purpose: Unit tests for shared screen helpers — date parsing, recency, buckets.

from __future__ import annotations

import datetime

from aethernews.screens.helpers import day_bucket, format_date, is_recent, parse_date


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _iso(hours_ago: int) -> str:
    return (_now() - datetime.timedelta(hours=hours_ago)).isoformat()


class TestParseDate:
    def test_iso_utc(self) -> None:
        dt = parse_date("2026-08-13T12:00:00Z")
        assert dt is not None
        assert dt.tzinfo is not None

    def test_rfc2822(self) -> None:
        dt = parse_date("Wed, 13 Aug 2026 12:00:00 +0000")
        assert dt is not None
        assert dt.tzinfo is not None

    def test_naive_becomes_utc(self) -> None:
        dt = parse_date("2026-08-13 12:00:00")
        assert dt is not None
        assert dt.utcoffset() == datetime.timedelta(0)

    def test_none_and_garbage(self) -> None:
        assert parse_date(None) is None
        assert parse_date("not a date") is None


class TestFormatDate:
    def test_iso(self) -> None:
        assert format_date("2026-08-13T12:00:00Z") == "2026-08-13"

    def test_rfc2822(self) -> None:
        assert format_date("Wed, 13 Aug 2026 12:00:00 +0000") == "2026-08-13"

    def test_empty(self) -> None:
        assert format_date(None) == "?"


class TestRecency:
    def test_recent_within_48h(self) -> None:
        assert is_recent(_iso(1)) is True
        assert is_recent(_iso(47)) is True

    def test_not_recent_beyond_48h(self) -> None:
        assert is_recent(_iso(49)) is False
        assert is_recent(_iso(24 * 5)) is False

    def test_garbage_not_recent(self) -> None:
        assert is_recent("junk") is False


class TestDayBucket:
    def test_today_is_zero(self) -> None:
        assert day_bucket(_iso(1)) == 0

    def test_yesterday_is_one(self) -> None:
        assert day_bucket(_iso(30)) == 1

    def test_week_old(self) -> None:
        assert day_bucket(_iso(24 * 8)) == 8

    def test_garbage_bucket_is_huge(self) -> None:
        assert day_bucket("junk") > 100_000
