# Created: 2026-08-12
# Last Edited: 2026-08-12 17:40 CT (America/Chicago)
# Path: tests/unit/test_rss.py
# Purpose: Unit tests for RSS helpers — date parsing, content extraction, bozo messaging.

from __future__ import annotations

from unittest.mock import MagicMock

from aethernews.rss import _bozo_exception_message, _parse_feed_date
from aethernews.screens.detail_help import html_to_text


class TestParseFeedDate:
    def test_iso_8601(self) -> None:
        dt = _parse_feed_date("2026-08-12T14:00:00+00:00")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 8
        assert dt.day == 12

    def test_rfc_2822(self) -> None:
        dt = _parse_feed_date("Wed, 12 Aug 2026 14:00:00 +0000")
        assert dt is not None

    def test_naive_iso(self) -> None:
        dt = _parse_feed_date("2026-08-12T14:00:00")
        assert dt is not None
        assert dt.tzinfo is not None  # should be made UTC-aware

    def test_none(self) -> None:
        assert _parse_feed_date(None) is None

    def test_garbage(self) -> None:
        assert _parse_feed_date("not-a-date") is None


class TestBozoExceptionMessage:
    def test_none(self) -> None:
        assert _bozo_exception_message(None) == "Unknown parsing error"

    def test_string_exception(self) -> None:
        assert _bozo_exception_message("bad xml") == "bad xml"

    def test_object_with_getMessage(self) -> None:
        exc = MagicMock()
        exc.getMessage.return_value = "SAX parse error"
        assert _bozo_exception_message(exc) == "SAX parse error"


class TestHtmlToText:
    def test_strips_tags_and_unescapes(self) -> None:
        raw = "<p>Hello &amp; <b>world</b></p>"
        assert html_to_text(raw) == "Hello & world"

    def test_preserves_paragraph_breaks(self) -> None:
        raw = "<p>First paragraph.</p><p>Second paragraph.</p>"
        assert html_to_text(raw) == "First paragraph.\n\nSecond paragraph."

    def test_handles_br(self) -> None:
        raw = "Line one<br>Line two"
        assert html_to_text(raw) == "Line one\nLine two"

    def test_strips_script_content(self) -> None:
        raw = "<script>var x = 1;</script><p>Real content</p>"
        assert html_to_text(raw) == "Real content"

    def test_none_and_empty(self) -> None:
        assert html_to_text(None) == ""
        assert html_to_text("") == ""
