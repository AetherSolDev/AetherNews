# Created: 2026-08-13
# Last Edited: 2026-08-14 16:43 CT (America/Chicago)
# Path: aethernews/fetcher.py
# Purpose: Fetch and extract full article text from a URL (readability-style).

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

# Short snippets that mark a page as a bot challenge / denial rather than a
# real article. Akamai ("Access Denied" / "Reference #18.") and PerimeterX
# denial pages are just long enough to pass naive length thresholds.
_BLOCKED_MARKERS = (
    "access denied",
    "you don't have permission to access",
    "reference #18.",
    "just a moment...",
    "verify you are human",
    "attention required",
    "sorry, you have been blocked",
)


def _is_blocked_page(text: str | None) -> bool:
    """Return ``True`` if *text* looks like a bot challenge or denial page."""
    if not text:
        return True
    lowered = text.lower()
    return any(marker in lowered for marker in _BLOCKED_MARKERS)


def _http_fetch(url: str, timeout: int = 20) -> bytes | None:
    """Fetch *url* over plain HTTP. Returns the raw body, or ``None`` on
    transport/blocking errors. A ``403`` (bot block) returns ``None``.
    """
    import urllib.error
    import urllib.request

    try:
        req = urllib.request.Request(
            url, headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.info("HTTP fetch failed for %s: %s", url, exc)
        return None


def _extract_html(raw: bytes | str | None) -> str | None:
    """Extract readable main text from raw HTML via trafilatura."""
    if not raw:
        return None
    import trafilatura  # lazy import — optional dependency

    try:
        text = trafilatura.extract(raw, include_comments=False,
                                   include_tables=False, favor_recall=True)
    except Exception as exc:
        logger.warning("Extraction failed: %s", exc)
        return None
    if not text:
        return None
    return text.strip()


def _browser_fetch(url: str, timeout: int = 30) -> str | None:
    """Load *url* in headless Chromium and return the page's inner text.

    Fallback for sites that block plain HTTP with bot checks. Requires the
    optional ``playwright`` package and a Chromium build. Returns ``None``
    when the page still shows a challenge (e.g. PerimeterX hold-to-confirm).
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("playwright not installed — skipping browser fallback")
        return None

    async def _run() -> str | None:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                try:
                    page = await browser.new_page()
                    await page.goto(url, timeout=timeout * 1000,
                                    wait_until="domcontentloaded")
                    await page.wait_for_timeout(1500)  # let JS challenges settle
                    text = await page.evaluate("document.body.innerText")
                    if text and not _is_blocked_page(text) and len(text.strip()) > 200:
                        return text.strip()
                    logger.info("Browser fetch blocked or yielded little content for %s", url)
                    return None
                finally:
                    await browser.close()
        except Exception as exc:
            logger.warning("Browser fetch failed for %s: %s", url, exc)
            return None

    return asyncio.run(_run())


async def fetch_article_text(url: str, timeout: int = 20) -> str | None:
    """Fetch and extract the full article text for *url*.

    Fast path: plain HTTP + trafilatura. If that is blocked (403/empty),
    fall back to headless Chromium (optional ``playwright``) which passes
    UA/fingerprint blocks. Returns ``None`` when both fail.
    """
    text = await asyncio.to_thread(_extract_html, _http_fetch(url, timeout))
    if text and not _is_blocked_page(text):
        return text
    logger.info("HTTP extraction blocked or empty for %s — trying headless browser", url)
    text = await asyncio.to_thread(_browser_fetch, url, max(timeout, 30))
    if text and not _is_blocked_page(text):
        return text
    logger.info("Browser extraction blocked or empty for %s", url)
    return None
