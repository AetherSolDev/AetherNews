# Created: 2026-08-12
# Last Edited: 2026-08-12 18:02 CT (America/Chicago)
# Path: aethernews/rss.py
# Purpose: RSS/Atom feed fetching and parsing — fetch_feed, fetch_feed_async, helpers.
#
# Adapted from AetherPod's aetherpod/rss.py.  News-flavored: articles carry
# full HTML content + author, and there is no audio-enclosure logic.

from __future__ import annotations

import asyncio
import contextlib
import datetime
import logging
import urllib.error
import urllib.request
from email import utils as email_utils
from typing import Any

from aethernews.models import Article, FeedResult

logger = logging.getLogger(__name__)

REFRESH_DAYS = 30
"""Default retention window: articles older than this are trimmed on refresh."""

MAX_ARTICLES_PER_FEED = 200
"""Cap on cached articles per feed — news is high-volume, keep state.json compact."""


def fetch_feed(url: str, timeout: int = 15,
               etag: str = "", last_modified: str = "") -> FeedResult:
    """Parse an RSS/Atom feed and return structured article data."""
    import feedparser  # lazy import — optional dependency

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AetherNews/1.0"})
        if etag:
            req.add_header("If-None-Match", etag)
        if last_modified:
            req.add_header("If-Modified-Since", last_modified)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            new_etag = resp.headers.get("ETag", "")
            new_lm = resp.headers.get("Last-Modified", "")
    except urllib.error.HTTPError as exc:
        if exc.code == 304:
            logger.debug("Feed unchanged (304): %s", url)
            return FeedResult(title="", articles=[], not_modified=True)
        logger.error("HTTP %d for %s: %s", exc.code, url, exc.reason)
        return FeedResult(title="", articles=[], error=f"HTTP {exc.code}: {exc.reason}")
    except urllib.error.URLError as exc:
        logger.error("URL error for %s: %s", url, exc.reason)
        return FeedResult(title="", articles=[], error=str(exc.reason))
    except TimeoutError:
        logger.error("Timeout fetching %s (%ds)", url, timeout)
        return FeedResult(title="", articles=[], error=f"Timeout after {timeout}s")
    except Exception as exc:
        logger.error("Failed to fetch %s: %s", url, exc)
        return FeedResult(title="", articles=[], error=f"Failed to fetch: {exc}")

    try:
        parsed = feedparser.parse(raw)
    except Exception as exc:
        logger.error("feedparser crash for %s: %s", url, exc)
        return FeedResult(title="", articles=[], error=f"Failed to parse feed: {exc}")

    if parsed.bozo and not parsed.entries:
        bozo_msg = _bozo_exception_message(parsed.bozo_exception)
        logger.warning("Bozo feed (no entries) at %s: %s", url, bozo_msg)
        return FeedResult(title="", articles=[], error=bozo_msg)

    feed_title = parsed.feed.get("title", url)
    articles: list[Article] = []

    for entry in parsed.entries:
        article_id = entry.get("id") or entry.get("link", "")
        content = entry.get("content")
        content = content[0].get("value") if isinstance(content, list) and content else None

        articles.append(
            Article(
                title=entry.get("title", "(no title)"),
                url=entry.get("link", ""),
                published=entry.get("published") or entry.get("updated"),
                summary=entry.get("summary"),
                content=content,
                author=entry.get("author"),
                article_id=article_id,
            )
        )

    logger.debug("Fetched %d articles from %s", len(articles), feed_title)
    return FeedResult(title=feed_title, articles=articles,
                      etag=new_etag, last_modified=new_lm)


def _bozo_exception_message(exception: Any) -> str:
    """Return a human-readable message from a feedparser bozo_exception."""
    if exception is None:
        return "Unknown parsing error"
    msg = str(exception)
    if hasattr(exception, "getMessage"):
        msg = exception.getMessage()
    return msg or "Unknown parsing error"


async def fetch_feed_async(url: str, timeout: int = 15,
                           etag: str = "", last_modified: str = "") -> FeedResult:
    """Async version of :func:`fetch_feed` using ``aiohttp``."""
    import aiohttp
    import feedparser  # lazy import — optional dependency

    headers = {"User-Agent": "AetherNews/1.0"}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    new_etag = ""
    new_lm = ""

    try:
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 304:
                    logger.debug("Feed unchanged (304): %s", url)
                    return FeedResult(title="", articles=[], not_modified=True)
                if resp.status >= 400:
                    reason = resp.reason or f"HTTP {resp.status}"
                    logger.error("HTTP %d for %s: %s", resp.status, url, reason)
                    return FeedResult(title="", articles=[], error=f"HTTP {resp.status}: {reason}")
                raw = await resp.read()
                new_etag = resp.headers.get("ETag", "")
                new_lm = resp.headers.get("Last-Modified", "")
    except asyncio.TimeoutError:
        logger.error("Timeout fetching %s (%ds)", url, timeout)
        return FeedResult(title="", articles=[], error=f"Timeout after {timeout}s")
    except aiohttp.ClientError as exc:
        logger.error("HTTP client error for %s: %s", url, exc)
        return FeedResult(title="", articles=[], error=str(exc))
    except Exception as exc:
        logger.error("Failed to fetch %s: %s", url, exc)
        return FeedResult(title="", articles=[], error=f"Failed to fetch: {exc}")

    try:
        parsed = feedparser.parse(raw)
    except Exception as exc:
        logger.error("feedparser crash for %s: %s", url, exc)
        return FeedResult(title="", articles=[], error=f"Failed to parse feed: {exc}")

    if parsed.bozo and not parsed.entries:
        bozo_msg = _bozo_exception_message(parsed.bozo_exception)
        logger.warning("Bozo feed (no entries) at %s: %s", url, bozo_msg)
        return FeedResult(title="", articles=[], error=bozo_msg)

    feed_title = parsed.feed.get("title", url)
    articles: list[Article] = []

    for entry in parsed.entries:
        article_id = entry.get("id") or entry.get("link", "")
        content = entry.get("content")
        content = content[0].get("value") if isinstance(content, list) and content else None

        articles.append(
            Article(
                title=entry.get("title", "(no title)"),
                url=entry.get("link", ""),
                published=entry.get("published") or entry.get("updated"),
                summary=entry.get("summary"),
                content=content,
                author=entry.get("author"),
                article_id=article_id,
            )
        )

    logger.debug("Fetched %d articles from %s (async)", len(articles), feed_title)
    return FeedResult(title=feed_title, articles=articles,
                      etag=new_etag, last_modified=new_lm)


def _parse_feed_date(raw: str) -> datetime.datetime | None:
    """Parse a feed date string (ISO 8601 or RFC 2822) to a UTC-aware datetime."""
    if not raw:
        return None
    raw = raw.strip()
    parsed: datetime.datetime | None = None
    with contextlib.suppress(ValueError, TypeError):
        parsed = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed is None:
        with contextlib.suppress(ValueError, TypeError, LookupError):
            parsed = email_utils.parsedate_to_datetime(raw)
    if parsed is not None and parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed
