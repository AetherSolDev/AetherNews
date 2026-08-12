# Created: 2026-08-12
# Last Edited: 2026-08-12 17:40 CT (America/Chicago)
# Path: tests/unit/test_engine.py
# Purpose: Unit tests for DataManager — state persistence, read/star/category management, retention.

from __future__ import annotations

import datetime
import json
import tempfile
from pathlib import Path

import pytest

from aethernews.engine import DataManager
from aethernews.models import Article, FeedResult


@pytest.fixture
def temp_state() -> Path:
    """Create a temporary state file path."""
    return Path(tempfile.mkstemp(suffix=".json")[1])


@pytest.fixture
def dm(temp_state: Path) -> DataManager:
    """Create a DataManager with a temp state file (empty)."""
    return DataManager(temp_state)


def _article(title: str, aid: str, published: str) -> Article:
    return Article(title=title, url=f"https://example.com/{aid}",
                   published=published, article_id=aid)


def _days_ago(n: int) -> str:
    dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=n)
    return dt.isoformat()


class TestDataManager:
    def test_init_creates_empty_state(self, dm: DataManager) -> None:
        assert dm.get_feeds() == []
        assert dm.unread_count() == 0

    def test_add_feed(self, dm: DataManager) -> None:
        assert dm.add_feed("https://example.com/feed.xml") is True
        assert dm.get_feeds() == ["https://example.com/feed.xml"]

    def test_add_feed_duplicate(self, dm: DataManager) -> None:
        dm.add_feed("https://example.com/feed.xml")
        assert dm.add_feed("https://example.com/feed.xml") is False
        assert len(dm.get_feeds()) == 1

    def test_remove_feed(self, dm: DataManager) -> None:
        dm.add_feed("https://example.com/feed.xml")
        assert dm.remove_feed("https://example.com/feed.xml") is True
        assert dm.get_feeds() == []
        assert dm.remove_feed("https://example.com/feed.xml") is False

    def test_remove_feed_cleans_cache_and_category(self, dm: DataManager) -> None:
        dm.add_feed("https://example.com/feed.xml")
        dm.set_category("https://example.com/feed.xml", "tech")
        dm.save_cached_result("https://example.com/feed.xml", FeedResult(
            title="Tech", articles=[_article("A", "a1", _days_ago(1))]))
        assert dm.get_category("https://example.com/feed.xml") == "tech"
        dm.remove_feed("https://example.com/feed.xml")
        assert dm.get_category("https://example.com/feed.xml") == ""
        assert dm.get_cached_result("https://example.com/feed.xml") is None

    def test_mark_read(self, dm: DataManager) -> None:
        dm.add_feed("https://example.com/feed.xml")
        dm.save_cached_result("https://example.com/feed.xml", FeedResult(
            title="T", articles=[_article("A", "a1", _days_ago(1))]))
        assert dm.is_unread("a1") is True
        assert dm.mark_read("a1") is True
        assert dm.is_unread("a1") is False
        assert dm.mark_read("a1") is False  # already read

    def test_toggle_read(self, dm: DataManager) -> None:
        assert dm.toggle_read("x") is True   # was read → now unread
        assert dm.toggle_read("x") is False  # was unread → now read

    def test_toggle_starred(self, dm: DataManager) -> None:
        assert dm.toggle_starred("x") is True
        assert dm.is_starred("x") is True
        assert dm.toggle_starred("x") is False
        assert dm.is_starred("x") is False

    def test_unread_count(self, dm: DataManager) -> None:
        dm.add_feed("https://example.com/feed.xml")
        dm.save_cached_result("https://example.com/feed.xml", FeedResult(
            title="T", articles=[_article("A", "a1", _days_ago(1)),
                                 _article("B", "a2", _days_ago(1))]))
        assert dm.unread_count() == 2
        dm.mark_read("a1")
        assert dm.unread_count() == 1

    def test_set_and_get_category(self, dm: DataManager) -> None:
        dm.add_feed("https://example.com/feed.xml")
        dm.set_category("https://example.com/feed.xml", "tech")
        assert dm.get_category("https://example.com/feed.xml") == "tech"
        assert dm.get_categories_list() == ["tech"]
        dm.set_category("https://example.com/feed.xml", "")
        assert dm.get_category("https://example.com/feed.xml") == ""
        assert dm.get_categories_list() == []

    def test_persistence_across_reload(self, temp_state: Path) -> None:
        dm1 = DataManager(temp_state)
        dm1.add_feed("https://example.com/feed.xml")
        dm1.toggle_starred("s1")
        dm1.set_category("https://example.com/feed.xml", "news")

        dm2 = DataManager(temp_state)
        assert dm2.get_feeds() == ["https://example.com/feed.xml"]
        assert dm2.is_starred("s1") is True
        assert dm2.get_category("https://example.com/feed.xml") == "news"

    def test_save_round_trip(self, temp_state: Path) -> None:
        dm1 = DataManager(temp_state)
        dm1.add_feed("https://example.com/feed.xml")
        dm1.save_cached_result("https://example.com/feed.xml", FeedResult(
            title="T", articles=[_article("A", "a1", _days_ago(1))]))
        data = json.loads(temp_state.read_text(encoding="utf-8"))
        assert data["version"] == DataManager.STATE_VERSION
        assert data["feeds"] == ["https://example.com/feed.xml"]
        assert data["feed_cache"]["https://example.com/feed.xml"]["articles"][0]["title"] == "A"

    def test_corrupt_state_starts_fresh(self, temp_state: Path) -> None:
        temp_state.write_text("{not json", encoding="utf-8")
        dm = DataManager(temp_state)
        assert dm.get_feeds() == []


class TestCacheAndRetention:
    def test_is_cache_fresh_within_ttl(self, dm: DataManager) -> None:
        dm.add_feed("https://example.com/feed.xml")
        dm.save_cached_result("https://example.com/feed.xml", FeedResult(
            title="T", articles=[_article("A", "a1", _days_ago(1))]))
        assert dm.is_cache_fresh("https://example.com/feed.xml") is True

    def test_uncached_is_never_fresh(self, dm: DataManager) -> None:
        assert dm.is_cache_fresh("https://example.com/other.xml") is False

    def test_touch_cache_bumps_freshness(self, dm: DataManager) -> None:
        dm.add_feed("https://example.com/feed.xml")
        dm.save_cached_result("https://example.com/feed.xml", FeedResult(
            title="T", articles=[_article("A", "a1", _days_ago(1))]))
        dm.touch_cache("https://example.com/feed.xml")
        assert dm.is_cache_fresh("https://example.com/feed.xml") is True
        assert len(dm.get_cached_result("https://example.com/feed.xml").articles) == 1

    def test_get_cached_result(self, dm: DataManager) -> None:
        dm.add_feed("https://example.com/feed.xml")
        dm.save_cached_result("https://example.com/feed.xml", FeedResult(
            title="T", articles=[_article("A", "a1", _days_ago(1))]))
        cached = dm.get_cached_result("https://example.com/feed.xml")
        assert cached is not None
        assert cached.title == "T"
        assert len(cached.articles) == 1
        assert cached.articles[0].title == "A"

    def test_save_cached_result_ignores_errors(self, dm: DataManager) -> None:
        dm.add_feed("https://example.com/feed.xml")
        dm.save_cached_result("https://example.com/feed.xml", FeedResult(
            title="", articles=[], error="boom"))
        assert dm.get_cached_result("https://example.com/feed.xml") is None

    def test_save_cached_result_ignores_not_modified(self, dm: DataManager) -> None:
        dm.add_feed("https://example.com/feed.xml")
        dm.save_cached_result("https://example.com/feed.xml", FeedResult(
            title="", articles=[], not_modified=True))
        assert dm.get_cached_result("https://example.com/feed.xml") is None

    def test_retention_trims_old_articles(self, dm: DataManager) -> None:
        dm.add_feed("https://example.com/feed.xml")
        articles = [
            _article("Old", "old", _days_ago(40)),
            _article("New", "new", _days_ago(1)),
        ]
        dm.save_cached_result("https://example.com/feed.xml", FeedResult(
            title="T", articles=articles))
        cached = dm.get_cached_result("https://example.com/feed.xml")
        assert cached is not None
        assert [a.title for a in cached.articles] == ["New"]
        assert len(cached.articles) == 1

    def test_retention_caps_at_max_articles(self, dm: DataManager) -> None:
        from aethernews.rss import MAX_ARTICLES_PER_FEED
        dm.add_feed("https://example.com/feed.xml")
        # All within the retention window so the per-feed cap is the bound.
        articles = [_article(f"A{i}", f"a{i}", _days_ago(i % 20))
                    for i in range(MAX_ARTICLES_PER_FEED + 50)]
        dm.save_cached_result("https://example.com/feed.xml", FeedResult(
            title="T", articles=articles))
        cached = dm.get_cached_result("https://example.com/feed.xml")
        assert cached is not None
        assert len(cached.articles) == MAX_ARTICLES_PER_FEED

    def test_pruned_unread_dropped(self, dm: DataManager) -> None:
        dm.add_feed("https://example.com/feed.xml")
        dm.save_cached_result("https://example.com/feed.xml", FeedResult(
            title="T", articles=[_article("Old", "old", _days_ago(40)),
                                 _article("New", "new", _days_ago(1))]))
        # "old" was pruned by retention, so its unread marker must go.
        assert dm.is_unread("old") is False
        assert dm.is_unread("new") is True

    def test_unread_by_feed(self, dm: DataManager) -> None:
        dm.add_feed("https://example.com/feed.xml")
        dm.save_cached_result("https://example.com/feed.xml", FeedResult(
            title="T", articles=[_article("A", "a1", _days_ago(1)),
                                 _article("B", "a2", _days_ago(1))]))
        assert dm.unread_by_feed("https://example.com/feed.xml") == 2
        dm.mark_read("a1")
        assert dm.unread_by_feed("https://example.com/feed.xml") == 1


class TestOpml:
    def test_opml_round_trip(self, dm: DataManager, tmp_path: Path) -> None:
        dm.add_feed("https://example.com/feed.xml")
        dm.add_feed("https://example.org/feed.xml")
        out = tmp_path / "subs.opml"
        assert dm.opml_export(str(out)) == 2
        assert out.exists()

        dm2 = DataManager(tmp_path / "state2.json")
        assert dm2.opml_import(str(out)) == 2
        assert set(dm2.get_feeds()) == {
            "https://example.com/feed.xml",
            "https://example.org/feed.xml",
        }

    def test_opml_import_skips_duplicates(self, dm: DataManager, tmp_path: Path) -> None:
        dm.add_feed("https://example.com/feed.xml")
        out = tmp_path / "subs.opml"
        dm.opml_export(str(out))
        assert dm.opml_import(str(out)) == 0

    def test_opml_import_missing_file(self, dm: DataManager, tmp_path: Path) -> None:
        assert dm.opml_import(str(tmp_path / "nope.opml")) == 0
