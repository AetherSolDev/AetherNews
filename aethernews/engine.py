# Created: 2026-08-12
# Last Edited: 2026-08-13 14:05 CT (America/Chicago)
# Path: aethernews/engine.py
# Purpose: DataManager — state persistence for feeds, unread/starred articles, categories.

from __future__ import annotations

import datetime
import json
import logging
import threading
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from platformdirs import user_state_dir

from aethernews.models import Article, FeedResult
from aethernews.rss import MAX_ARTICLES_PER_FEED, REFRESH_DAYS, _parse_feed_date

logger = logging.getLogger(__name__)


class DataManager:
    """Manages persistent state: feed URLs, read/unread + starred articles, categories.

    Reads/writes a JSON file at the configured path. Thread-safe for
    single-process use via an internal lock.

    Retention is INVERTED vs AetherPod: news is high-volume and short-lived,
    so the cache is trimmed to the newest articles rather than merged into
    full history.
    """

    STATE_VERSION = 1
    """Current schema version for ``state.json``."""

    DEFAULT_CACHE_TTL_HOURS = 6
    """Default cache-freshness window: feeds fetched within this many hours
    are considered fresh and skipped by TTL-gated refreshes."""

    # ── persistence ────────────────────────────────────────────────

    def __init__(self, path: str | Path | None = None) -> None:
        if path is None:
            path = Path(user_state_dir("aethernews", ensure_exists=True)) / "state.json"
        self._path = Path(path)
        self._lock = threading.Lock()
        self._feeds: list[str] = []
        self._unread: set[str] = set()
        self._starred: set[str] = set()
        self._categories: dict[str, str] = {}
        self._feed_headers: dict[str, dict[str, str]] = {}
        self._feed_cache: dict[str, dict[str, Any]] = {}
        self._cache_ttl_hours: float = self.DEFAULT_CACHE_TTL_HOURS
        self.load()

    def load(self) -> None:
        """Load state from disk. If the file is missing or corrupt, start empty."""
        with self._lock:
            if not self._path.exists():
                logger.info("No state file at %s — starting fresh", self._path)
                self._reset_empty()
                return
            try:
                raw = self._path.read_text(encoding="utf-8")
                data: dict[str, Any] = json.loads(raw)
                self._feeds = data.get("feeds", [])
                unread_raw = data.get("unread", [])
                self._unread = set(unread_raw) if isinstance(unread_raw, list) else set()
                starred_raw = data.get("starred", [])
                self._starred = set(starred_raw) if isinstance(starred_raw, list) else set()
                self._categories = data.get("categories", {})
                self._feed_headers = data.get("feed_headers", {})
                self._feed_cache = data.get("feed_cache", {})
                self._cache_ttl_hours = float(
                    data.get("cache_ttl_hours", self.DEFAULT_CACHE_TTL_HOURS)
                )
                logger.debug("Loaded %d feeds, %d unread, %d starred, %d cached",
                             len(self._feeds), len(self._unread), len(self._starred),
                             len(self._feed_cache))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load state: %s — starting fresh", exc)
                self._reset_empty()

    def _reset_empty(self) -> None:
        self._feeds = []
        self._unread = set()
        self._starred = set()
        self._categories = {}
        self._feed_headers = {}
        self._feed_cache = {}
        self._cache_ttl_hours = self.DEFAULT_CACHE_TTL_HOURS

    def save(self) -> None:
        """Persist current state to disk atomically."""
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "version": self.STATE_VERSION,
                "feeds": list(self._feeds),
                "unread": sorted(self._unread),
                "starred": sorted(self._starred),
                "categories": dict(self._categories),
                "feed_headers": dict(self._feed_headers),
                "cache_ttl_hours": self._cache_ttl_hours,
                "feed_cache": dict(self._feed_cache),
            }
            tmp = self._path.with_suffix(".tmp")
            try:
                tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
                tmp.replace(self._path)
            except OSError as exc:
                logger.error("Failed to save state: %s", exc)
                raise

    # ── feed management ────────────────────────────────────────────

    def add_feed(self, url: str) -> bool:
        """Add a feed URL if not already present. Returns True if added."""
        if url in self._feeds:
            return False
        self._feeds.append(url)
        self.save()
        logger.info("Added feed: %s", url)
        return True

    def remove_feed(self, url: str) -> bool:
        """Remove a feed URL. Returns True if it existed."""
        if url not in self._feeds:
            return False
        self._feeds.remove(url)
        self._feed_cache.pop(url, None)
        self._feed_headers.pop(url, None)
        self._categories.pop(url, None)
        self.save()
        logger.info("Removed feed: %s", url)
        return True

    def get_feeds(self) -> list[str]:
        """Return a copy of the feed URL list."""
        return list(self._feeds)

    def get_cache_ttl(self) -> float:
        """Return the cache-freshness window in hours."""
        return self._cache_ttl_hours

    def set_cache_ttl(self, hours: float) -> None:
        """Set the cache-freshness TTL (hours) and persist."""
        self._cache_ttl_hours = max(0.0, float(hours))
        self.save()
        logger.debug("Cache TTL set to %.1f hours", self._cache_ttl_hours)

    # ── article tracking ───────────────────────────────────────────

    def mark_read(self, article_id: str) -> bool:
        """Mark an article as read. Returns True if it was unread."""
        with self._lock:
            if article_id not in self._unread:
                return False
            self._unread.discard(article_id)
        self.save()
        logger.debug("Marked read: %s", article_id)
        return True

    def is_unread(self, article_id: str) -> bool:
        """Check if an article is unread (thread-safe)."""
        with self._lock:
            return article_id in self._unread

    def unread_count(self) -> int:
        """Return the number of unread articles across all feeds."""
        with self._lock:
            return len(self._unread)

    def toggle_read(self, article_id: str) -> bool:
        """Toggle read/unread state. Returns True if now unread."""
        with self._lock:
            if article_id in self._unread:
                self._unread.discard(article_id)
                now_unread = False
            else:
                self._unread.add(article_id)
                now_unread = True
        self.save()
        logger.debug("Toggled read state for %s (unread=%s)", article_id, now_unread)
        return now_unread

    def toggle_starred(self, article_id: str) -> bool:
        """Toggle starred state. Returns True if now starred."""
        with self._lock:
            if article_id in self._starred:
                self._starred.discard(article_id)
                now_starred = False
            else:
                self._starred.add(article_id)
                now_starred = True
        self.save()
        logger.debug("Toggled starred for %s (starred=%s)", article_id, now_starred)
        return now_starred

    def is_starred(self, article_id: str) -> bool:
        """Check if an article is starred (thread-safe)."""
        with self._lock:
            return article_id in self._starred

    def mark_all_unread(self, url: str) -> int:
        """Mark every cached article in *url*'s feed as unread.

        Returns the number of articles marked.  Useful to recover a
        backlog whose read state was corrupted (e.g. the old
        ``_mark_new_unread`` mutation bug).
        """
        with self._lock:
            entry = self._feed_cache.get(url)
            if entry is None:
                return 0
            count = 0
            for a in entry.get("articles", []):
                aid = a.get("article_id")
                if aid and aid not in self._unread:
                    self._unread.add(aid)
                    count += 1
        self.save()
        logger.info("Marked %d articles unread for %s", count, url)
        return count

    def get_starred(self) -> set[str]:
        """Return a copy of the starred article-id set."""
        with self._lock:
            return set(self._starred)

    # ── categories ─────────────────────────────────────────────────

    def set_category(self, url: str, category: str) -> None:
        """Assign a category name to a feed URL (persisted)."""
        with self._lock:
            if category:
                self._categories[url] = category
            else:
                self._categories.pop(url, None)
        self.save()
        logger.info("Feed %s → category %r", url, category)

    def get_category(self, url: str) -> str:
        """Return the category for a feed URL, or ``""`` if unset."""
        with self._lock:
            return self._categories.get(url, "")

    def get_categories(self) -> dict[str, str]:
        """Return a copy of the URL → category mapping."""
        with self._lock:
            return dict(self._categories)

    def get_categories_list(self) -> list[str]:
        """Return the sorted unique list of category names in use."""
        with self._lock:
            return sorted({c for c in self._categories.values() if c})

    def rename_category(self, old: str, new: str) -> int:
        """Rename every feed assigned to *old* to *new*.

        Returns the number of feeds re-tagged.  If *new* is empty the
        category is cleared (feeds fall back to Uncategorized).
        """
        with self._lock:
            count = 0
            for url, cat in list(self._categories.items()):
                if cat == old:
                    if new:
                        self._categories[url] = new
                    else:
                        del self._categories[url]
                    count += 1
        self.save()
        logger.info("Renamed category %r → %r (%d feeds)", old, new, count)
        return count

    def merge_category(self, old: str, new: str) -> int:
        """Re-tag all feeds in *old* into the existing *new* category.

        Returns the number of feeds moved.  *new* must already exist (or
        be empty to clear); this does not create new categories.
        """
        with self._lock:
            count = 0
            for url, cat in self._categories.items():
                if cat == old:
                    self._categories[url] = new
                    count += 1
        self.save()
        logger.info("Merged category %r into %r (%d feeds)", old, new, count)
        return count

    # ── conditional fetch headers ──────────────────────────────────

    def get_feed_headers(self, url: str) -> dict[str, str]:
        """Return stored ETag/Last-Modified headers for a feed URL."""
        with self._lock:
            return dict(self._feed_headers.get(url, {}))

    def save_feed_headers(self, url: str, etag: str = "", last_modified: str = "") -> None:
        """Persist ETag and/or Last-Modified for a feed URL."""
        with self._lock:
            headers: dict[str, str] = {}
            if etag:
                headers["etag"] = etag
            if last_modified:
                headers["last_modified"] = last_modified
            if headers:
                self._feed_headers[url] = headers
            else:
                self._feed_headers.pop(url, None)
        self.save()

    # ── feed result cache ──────────────────────────────────────────

    @staticmethod
    def _parse_checked_at(raw: str | None) -> datetime.datetime | None:
        """Parse a stored ``checked_at`` ISO string into a UTC-aware datetime."""
        if not raw:
            return None
        try:
            dt = datetime.datetime.fromisoformat(raw)
        except (ValueError, TypeError):
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt

    @staticmethod
    def _utc_now() -> datetime.datetime:
        return datetime.datetime.now(datetime.timezone.utc)

    def last_checked(self, url: str) -> str | None:
        """Return the ISO timestamp of the last successful fetch for *url*."""
        with self._lock:
            entry = self._feed_cache.get(url)
        if entry is None:
            return None
        checked = self._parse_checked_at(entry.get("checked_at"))
        return checked.isoformat() if checked else None

    def is_cache_fresh(self, url: str, max_age: float | None = None) -> bool:
        """Return True if *url* has a cache entry checked within *max_age* hours.

        When *max_age* is ``None``, uses the configured TTL.
        A missing cache entry is never fresh.
        """
        if max_age is None:
            max_age = self._cache_ttl_hours
        with self._lock:
            entry = self._feed_cache.get(url)
        if entry is None:
            return False
        checked = self._parse_checked_at(entry.get("checked_at"))
        if checked is None:
            return False
        age = (self._utc_now() - checked).total_seconds() / 3600
        return age <= max_age

    def get_cached_result(self, url: str, max_age: float | None = None) -> FeedResult | None:
        """Return a cached ``FeedResult`` for *url*, or ``None``.

        When *max_age* is given, an entry checked longer ago than
        *max_age* hours is treated as absent (stale).
        """
        with self._lock:
            entry = self._feed_cache.get(url)
        if entry is None:
            return None
        if max_age is not None and not self.is_cache_fresh(url, max_age):
            return None
        articles = [
            Article(
                title=a.get("title", "(no title)"),
                url=a.get("url", ""),
                published=a.get("published"),
                summary=a.get("summary"),
                content=a.get("content"),
                author=a.get("author"),
                article_id=a.get("article_id"),
            )
            for a in entry.get("articles", [])
        ]
        return FeedResult(title=entry.get("title", url), articles=articles)

    def save_cached_result(self, url: str, result: FeedResult) -> None:
        """Cache a successful ``FeedResult`` for *url*.

        Records ``checked_at`` (UTC ISO) so TTL-gated refreshes can
        decide whether the entry is still fresh.

        Retention is INVERTED vs AetherPod: instead of merging into full
        history, the cache is REPLACED by the fresh fetch (which pulls the
        feed's full document) then TRIM-capped to the newest
        ``MAX_ARTICLES_PER_FEED`` within the ``REFRESH_DAYS`` window.
        Articles that fall off the cap are dropped from ``unread`` so the
        unread set never grows unboundedly.

        Newly-seen article IDs are added to the unread set; IDs that were
        already cached (and possibly marked read) keep their state.
        """
        if result.error or result.not_modified:
            return
        new_articles = [
            {
                "title": a.title,
                "url": a.url,
                "published": a.published,
                "summary": a.summary,
                "content": a.content,
                "author": a.author,
                "article_id": a.article_id,
            }
            for a in result.articles
        ]
        with self._lock:
            prev = self._feed_cache.get(url)
            if prev is None or not isinstance(prev.get("articles"), list):
                prev = None
            kept = self._trim_articles(new_articles)
            self._drop_pruned_unread(url, kept)
            self._mark_new_unread(url, kept, prev)
            entry = {
                "title": result.title,
                "checked_at": self._utc_now().isoformat(),
                "articles": kept,
            }
            self._feed_cache[url] = entry
        self.save()

    def _mark_new_unread(
        self, url: str, kept: list[dict[str, Any]], prev: dict[str, Any] | None
    ) -> None:
        """Add newly-seen article IDs to the unread set.

        Only IDs not present in the *previous* cache entry for *url* are
        marked unread, so already-known (possibly read) articles keep
        their read state.  ``prev`` must be the cache entry *before* the
        current save (not the mutated in-progress entry).  Caller must
        hold ``_lock``.
        """
        known: set[str] = set()
        if prev is not None:
            known = {a.get("article_id") for a in prev.get("articles", [])}
        for a in kept:
            aid = a.get("article_id")
            if aid and aid not in known:
                self._unread.add(aid)

    def _trim_articles(self, articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Trim *articles* to the retention window + per-feed cap.

        Returns articles sorted newest-first.  Caller must hold ``_lock``.
        """
        cutoff = self._utc_now() - datetime.timedelta(days=REFRESH_DAYS)
        kept: list[dict[str, Any]] = []
        for a in articles:
            published = _parse_feed_date(a.get("published") or "")
            if published is not None and published < cutoff:
                continue
            kept.append(a)
        kept.sort(key=lambda a: _parse_feed_date(a.get("published") or "")
                   or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc),
                  reverse=True)
        return kept[:MAX_ARTICLES_PER_FEED]

    def _drop_pruned_unread(
        self, url: str, kept: list[dict[str, Any]]
    ) -> None:
        """Clear unread markers for articles that are no longer cached.

        A pruned article can never come back (news is replaced, not merged),
        so leaving it ``unread`` would inflate the unread count forever.
        Caller must hold ``_lock``.
        """
        kept_ids = {a.get("article_id") for a in kept}
        for uid in list(self._unread):
            if uid not in kept_ids and not self._url_contains_article(url, uid):
                self._unread.discard(uid)

    def _url_contains_article(self, url: str, article_id: str) -> bool:
        """Return True if *article_id* exists in *url*'s cache entry."""
        entry = self._feed_cache.get(url)
        if entry is None:
            return False
        return any(a.get("article_id") == article_id for a in entry.get("articles", []))

    def touch_cache(self, url: str) -> None:
        """Refresh the ``checked_at`` timestamp of an existing cache entry.

        Called when a conditional GET returns ``304 Not Modified``: the
        feed was verified unchanged, so its freshness window is reset
        without touching the cached article list.
        """
        with self._lock:
            entry = self._feed_cache.get(url)
            if entry is None:
                return
            entry["checked_at"] = self._utc_now().isoformat()
        self.save()

    def unread_by_feed(self, url: str) -> int:
        """Return the number of unread articles in *url*'s cache."""
        with self._lock:
            entry = self._feed_cache.get(url)
            if entry is None:
                return 0
            return sum(
                1 for a in entry.get("articles", [])
                if a.get("article_id") in self._unread
            )

    def total_unread(self) -> int:
        """Return the total unread count across all feeds."""
        with self._lock:
            return len(self._unread)

    # ── feed freshness / recency ────────────────────────────────

    RECENT_HOURS = 24
    """Default window for the "recently updated" marker on the overview."""

    def feed_updated(self, url: str) -> datetime.datetime | None:
        """Return when *url* was last updated (newest article publish date).

        Falls back to the cache entry's ``checked_at`` only when the feed
        has no cached articles (e.g. a brand-new subscription).  ``None``
        when there is no cache entry at all.

        Article publish date is preferred over fetch time so overview
        ordering and recency reflect *content* freshness, not how recently
        the cache happened to be checked.
        """
        with self._lock:
            entry = self._feed_cache.get(url)
        if entry is None:
            return None
        latest: datetime.datetime | None = None
        for a in entry.get("articles", []):
            published = _parse_feed_date(a.get("published") or "")
            if published is not None and (
                latest is None or published > latest
            ):
                latest = published
        if latest is not None:
            return latest
        return self._parse_checked_at(entry.get("checked_at"))

    def recently_updated(self, url: str, hours: float | None = None) -> bool:
        """Return True if *url* has fresh content within *hours* (default 24).

        A feed is "recent" when its newest cached article was published
        inside the window.  A feed with no cached articles is recent only
        when its cache was checked inside the window.
        """
        if hours is None:
            hours = self.RECENT_HOURS
        with self._lock:
            entry = self._feed_cache.get(url)
        if entry is None:
            return False
        latest: datetime.datetime | None = None
        for a in entry.get("articles", []):
            published = _parse_feed_date(a.get("published") or "")
            if published is not None and (
                latest is None or published > latest
            ):
                latest = published
        if latest is None:
            latest = self._parse_checked_at(entry.get("checked_at"))
        if latest is None:
            return False
        cutoff = self._utc_now() - datetime.timedelta(hours=hours)
        return latest > cutoff

    def group_summary(self, category: str) -> dict[str, Any]:
        """Aggregate stats for a category group header.

        Returns ``{"urls", "unread", "recent", "updated"}`` where ``urls``
        is the list of feed URLs in *category*, ``unread`` the total unread
        count, ``recent`` whether any feed in the group has fresh content,
        and ``updated`` the newest ``feed_updated`` timestamp among them.
        """
        urls = [
            u for u in self._feeds if self.get_category(u) == category
        ]
        if category == "":
            urls = [
                u for u in self._feeds if not self.get_category(u)
            ]
        unread = sum(self.unread_by_feed(u) for u in urls)
        updated: datetime.datetime | None = None
        recent = False
        for u in urls:
            u_time = self.feed_updated(u)
            if u_time is not None and (updated is None or u_time > updated):
                updated = u_time
            if self.recently_updated(u):
                recent = True
        return {
            "urls": urls,
            "unread": unread,
            "recent": recent,
            "updated": updated,
        }

    # ── OPML import / export ─────────────────────────────────────────

    def opml_import(self, file_path: str | Path) -> int:
        """Import feed URLs from an OPML file.

        Parses the OPML 1.0/2.0 XML structure and extracts every
        ``<outline>`` element with an ``xmlUrl`` attribute.  URLs that
        are not already subscribed are added via :meth:`add_feed`.

        Returns the number of *new* feeds added (omitting duplicates).
        """
        path = Path(file_path)
        if not path.exists():
            logger.warning("OPML file not found: %s", path)
            return 0

        try:
            tree = ET.parse(path)
            root = tree.getroot()
        except (ET.ParseError, OSError) as exc:
            logger.error("Failed to parse OPML %s: %s", path, exc)
            return 0

        count = 0
        for outline in root.iter("outline"):
            url = outline.get("xmlUrl", "")
            if url and self.add_feed(url):
                count += 1

        logger.info("Imported %d new feeds from %s", count, path)
        return count

    def opml_export(self, file_path: str | Path) -> int:
        """Export subscribed feeds to an OPML 2.0 file.

        Generates a standard OPML 2.0 document containing the current
        list of feed URLs as ``<outline>`` elements, then writes it to
        *file_path*.

        Returns the number of feeds exported.
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        opml = ET.Element("opml", version="2.0")
        head = ET.SubElement(opml, "head")
        title = ET.SubElement(head, "title")
        title.text = "AetherNews subscriptions"
        body = ET.SubElement(opml, "body")

        for feed_url in self._feeds:
            outline = ET.SubElement(body, "outline")
            outline.set("text", feed_url)
            outline.set("title", feed_url)
            outline.set("type", "rss")
            outline.set("xmlUrl", feed_url)

        tree = ET.ElementTree(opml)
        ET.indent(tree, space="  ")

        try:
            tree.write(str(path), encoding="utf-8", xml_declaration=True)
        except OSError as exc:
            logger.error("Failed to write OPML %s: %s", path, exc)
            return 0

        count = len(self._feeds)
        logger.info("Exported %d feeds to %s", count, path)
        return count
