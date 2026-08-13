# Created: 2026-08-12
# Last Edited: 2026-08-13 12:12 CT (America/Chicago)
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


def _hours_ago(n: int) -> str:
    dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=n)
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

    def test_rename_category_retags_all_feeds(self, dm: DataManager) -> None:
        for i in range(3):
            dm.add_feed(f"https://example.com/f{i}.xml")
        for i in range(3):
            dm.set_category(f"https://example.com/f{i}.xml", "Tech")
        dm.add_feed("https://example.com/other.xml")
        dm.set_category("https://example.com/other.xml", "News")

        assert dm.rename_category("Tech", "Technology") == 3
        assert dm.get_categories_list() == ["News", "Technology"]
        assert all(
            dm.get_category(f"https://example.com/f{i}.xml") == "Technology"
            for i in range(3)
        )
        assert dm.get_category("https://example.com/other.xml") == "News"

    def test_rename_category_clear_uncategorizes(self, dm: DataManager) -> None:
        dm.add_feed("https://example.com/f.xml")
        dm.set_category("https://example.com/f.xml", "Tech")
        assert dm.rename_category("Tech", "") == 1
        assert dm.get_category("https://example.com/f.xml") == ""
        assert dm.get_categories_list() == []

    def test_rename_category_unknown_returns_zero(self, dm: DataManager) -> None:
        assert dm.rename_category("Nope", "Yes") == 0

    def test_merge_category_moves_feeds(self, dm: DataManager) -> None:
        dm.add_feed("https://example.com/a.xml")
        dm.add_feed("https://example.com/b.xml")
        dm.set_category("https://example.com/a.xml", "Tech")
        dm.set_category("https://example.com/b.xml", "News")
        assert dm.merge_category("Tech", "News") == 1
        assert dm.get_categories_list() == ["News"]

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

    def test_new_articles_unread_on_refresh(self, dm: DataManager) -> None:
        """Regression: new articles on a later refresh must be marked unread.

        A bug mutated the cache entry before diffing, so the "known" set
        always matched the new articles and nothing was ever marked unread.
        """
        dm.add_feed("https://example.com/feed.xml")
        dm.save_cached_result("https://example.com/feed.xml", FeedResult(
            title="T", articles=[_article("A", "a1", _hours_ago(2)),
                                 _article("B", "a2", _hours_ago(3))]))
        assert dm.is_unread("a1") is True
        assert dm.is_unread("a2") is True

        # a1 was read; a2 stays unread
        dm.mark_read("a1")

        # Second refresh: same articles + a new one (a3).
        dm.save_cached_result("https://example.com/feed.xml", FeedResult(
            title="T", articles=[_article("A", "a1", _hours_ago(2)),
                                 _article("B", "a2", _hours_ago(3)),
                                 _article("C", "a3", _hours_ago(1))]))
        # a1 keeps read state, a2 stays unread, a3 is newly unread.
        assert dm.is_unread("a1") is False
        assert dm.is_unread("a2") is True
        assert dm.is_unread("a3") is True

    def test_mark_all_unread_recovers_backlog(self, dm: DataManager) -> None:
        dm.add_feed("https://example.com/feed.xml")
        dm.save_cached_result("https://example.com/feed.xml", FeedResult(
            title="T", articles=[_article("A", "a1", _hours_ago(2)),
                                 _article("B", "a2", _hours_ago(3))]))
        dm.mark_read("a1")
        dm.mark_read("a2")
        assert dm.unread_by_feed("https://example.com/feed.xml") == 0
        assert dm.mark_all_unread("https://example.com/feed.xml") == 2
        assert dm.unread_by_feed("https://example.com/feed.xml") == 2
        # idempotent — already unread articles aren't double-counted
        assert dm.mark_all_unread("https://example.com/feed.xml") == 0


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


class TestFetchedBodies:
    def test_get_fetched_body_default_empty(self, dm: DataManager) -> None:
        assert dm.get_fetched_body("a1") == ""

    def test_save_and_get_fetched_body(self, dm: DataManager) -> None:
        dm.save_fetched_body("a1", "Full article body text")
        assert dm.get_fetched_body("a1") == "Full article body text"

    def test_save_empty_clears(self, dm: DataManager) -> None:
        dm.save_fetched_body("a1", "Body")
        dm.save_fetched_body("a1", "")
        assert dm.get_fetched_body("a1") == ""

    def test_fetched_body_persists_across_reload(self, temp_state: Path) -> None:
        dm1 = DataManager(temp_state)
        dm1.save_fetched_body("a1", "Persisted body")
        dm2 = DataManager(temp_state)
        assert dm2.get_fetched_body("a1") == "Persisted body"


class TestFeedFreshness:
    def test_feed_updated_uses_newest_article(self, dm: DataManager) -> None:
        dm.add_feed("https://example.com/feed.xml")
        dm.save_cached_result("https://example.com/feed.xml", FeedResult(
            title="T", articles=[_article("Old", "old", _days_ago(3)),
                                 _article("New", "new", _hours_ago(1))]))
        updated = dm.feed_updated("https://example.com/feed.xml")
        assert updated is not None
        age_hours = (datetime.datetime.now(datetime.timezone.utc) - updated).total_seconds() / 3600
        assert age_hours < 24  # within ~1 day of the newest article

    def test_feed_updated_none_for_uncached(self, dm: DataManager) -> None:
        assert dm.feed_updated("https://example.com/unknown.xml") is None

    def test_feed_updated_falls_back_to_checked_at(self, dm: DataManager) -> None:
        dm.add_feed("https://example.com/feed.xml")
        dm.save_cached_result("https://example.com/feed.xml", FeedResult(
            title="T", articles=[]))
        assert dm.feed_updated("https://example.com/feed.xml") is not None

    def test_recently_updated_within_24h(self, dm: DataManager) -> None:
        dm.add_feed("https://example.com/feed.xml")
        dm.save_cached_result("https://example.com/feed.xml", FeedResult(
            title="T", articles=[_article("A", "a1", _hours_ago(1))]))
        assert dm.recently_updated("https://example.com/feed.xml") is True
        assert dm.recently_updated("https://example.com/unknown.xml") is False

    def test_recently_updated_beyond_window(self, temp_state: Path) -> None:
        dm = DataManager(temp_state)
        dm.add_feed("https://example.com/feed.xml")
        dm.save_cached_result("https://example.com/feed.xml", FeedResult(
            title="T", articles=[_article("Old", "old", _days_ago(5))]))
        # Rewind the check timestamp so both the article and the fetch
        # fall outside the window.
        raw = json.loads(temp_state.read_text(encoding="utf-8"))
        old_check = (datetime.datetime.now(datetime.timezone.utc)
                     - datetime.timedelta(days=5)).isoformat()
        raw["feed_cache"]["https://example.com/feed.xml"]["checked_at"] = old_check
        temp_state.write_text(json.dumps(raw), encoding="utf-8")
        dm2 = DataManager(temp_state)
        assert dm2.recently_updated("https://example.com/feed.xml", hours=24) is False

    def test_group_summary_buckets_categories(self, dm: DataManager) -> None:
        tech = "https://example.com/tech.xml"
        news = "https://example.com/news.xml"
        uncat = "https://example.com/uncat.xml"
        dm.add_feed(tech)
        dm.add_feed(news)
        dm.add_feed(uncat)
        dm.set_category(tech, "Tech")
        dm.set_category(news, "News")
        dm.save_cached_result(tech, FeedResult(
            title="Tech", articles=[_article("A", "a1", _hours_ago(1))]))

        tech_summary = dm.group_summary("Tech")
        assert tech_summary["urls"] == [tech]
        assert tech_summary["unread"] == 1
        assert tech_summary["recent"] is True
        assert tech_summary["updated"] is not None

        news_summary = dm.group_summary("News")
        assert news_summary["urls"] == [news]
        assert news_summary["unread"] == 0
        assert news_summary["recent"] is False

        uncat_summary = dm.group_summary("")
        assert uncat_summary["urls"] == [uncat]
        assert uncat_summary["unread"] == 0
