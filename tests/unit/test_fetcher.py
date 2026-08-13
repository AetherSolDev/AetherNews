# Created: 2026-08-13
# Last Edited: 2026-08-13 17:19 CT (America/Chicago)
# Path: tests/unit/test_fetcher.py
# Purpose: Unit tests for fetch_article_text (trafilatura extraction) — no external network.

from __future__ import annotations

import asyncio
import http.server
import threading

import pytest

from aethernews.fetcher import fetch_article_text


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        body = (
            b"<html><head><title>Test</title></head><body>"
            b"<nav>nav junk</nav>"
            b"<article>"
            b"<h1>Test Headline</h1>"
            b"<p>This is the first paragraph of the article body.</p>"
            b"<p>This is the second paragraph with useful content.</p>"
            b"</article>"
            b"<footer>footer junk</footer>"
            b"</body></html>"
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:  # type: ignore[no-untyped-def]
        pass


@pytest.fixture
def article_url() -> str:
    server = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}/article"
    server.shutdown()


def test_fetch_article_text_extracts_body(article_url: str) -> None:
    text = asyncio.run(fetch_article_text(article_url, timeout=5))
    assert text is not None
    assert "Test Headline" in text
    assert "first paragraph of the article body" in text
    assert "nav junk" not in text
    assert "footer junk" not in text


def test_fetch_article_text_missing_page() -> None:
    # Non-routable / refused connection — should return None, not raise.
    text = asyncio.run(fetch_article_text("http://127.0.0.1:1/nope", timeout=3))
    assert text is None


def test_browser_fallback_used_when_http_blocked(monkeypatch) -> None:
    """When plain HTTP yields nothing, the headless-browser fallback runs."""
    from aethernews import fetcher

    called = {}

    def fake_http_fetch(url, timeout):
        called["http"] = True

    def fake_browser_fetch(url, timeout):
        called["browser"] = True
        return "Extracted by headless browser body text here."

    monkeypatch.setattr(fetcher, "_http_fetch", fake_http_fetch)
    monkeypatch.setattr(fetcher, "_browser_fetch", fake_browser_fetch)

    text = asyncio.run(fetcher.fetch_article_text("https://example.com/x", timeout=5))
    assert text == "Extracted by headless browser body text here."
    assert called.get("http") is True
    assert called.get("browser") is True


def test_browser_fallback_skipped_when_http_succeeds(monkeypatch) -> None:
    """Fast HTTP path wins; the browser is not invoked when it succeeds."""
    from aethernews import fetcher

    called = {}

    def fake_http_fetch(url, timeout):
        called["http"] = True
        return b"<html><body><article><p>Fast path body.</p></article></body></html>"

    def fake_browser_fetch(url, timeout):
        called["browser"] = True
        return "Should not be used."

    monkeypatch.setattr(fetcher, "_http_fetch", fake_http_fetch)
    monkeypatch.setattr(fetcher, "_browser_fetch", fake_browser_fetch)

    text = asyncio.run(fetcher.fetch_article_text("https://example.com/x", timeout=5))
    assert "Fast path body." in text
    assert "browser" not in called
