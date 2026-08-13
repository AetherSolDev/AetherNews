import asyncio
import tempfile
from pathlib import Path

import pytest
from textual.widgets._tree import Tree

from aethernews.app import AetherNews
from aethernews.engine import DataManager
from aethernews.models import Article, FeedResult
from aethernews.screens.feed_screen import UNCATEGORIZED, FeedScreen, _FeedData, _GroupData


def _article(title, aid, published):
    return Article(title=title, url=f"https://example.com/{aid}", published=published, article_id=aid)


def _seed_state(path):
    import datetime as dt
    now = dt.datetime.now(dt.timezone.utc)
    def hours_ago(n):
        return (now - dt.timedelta(hours=n)).strftime("%Y-%m-%dT%H:%M:%SZ")
    dm = DataManager(path)
    tech_new = "https://example.com/tech.xml"
    tech_old = "https://example.com/tech2.xml"
    news = "https://example.com/news.xml"
    dm.add_feed(tech_new); dm.add_feed(tech_old); dm.add_feed(news)
    dm.set_category(tech_new, "Tech"); dm.set_category(tech_old, "Tech"); dm.set_category(news, "News")
    dm.save_cached_result(tech_new, FeedResult(title="LWN", articles=[_article("A1","a1",hours_ago(2))]))
    dm.save_cached_result(tech_old, FeedResult(title="Hacker News", articles=[_article("A2","a2",hours_ago(72))]))
    dm.save_cached_result(news, FeedResult(title="BBC", articles=[_article("A3","a3",hours_ago(30))]))


def _tree_nodes(tree):
    out = []
    def walk(node):
        out.append((node.label.plain, node.data))
        for child in node.children:
            walk(child)
    walk(tree.root)
    return out


@pytest.fixture
def state_path():
    return Path(tempfile.mkstemp(suffix=".json")[1])


def test_groups_rendered_and_newest_first(state_path):
    _seed_state(state_path)
    def run():
        app = AetherNews(data_path=state_path)
        async def main():
            async with app.run_test() as pilot:
                await pilot.pause()
                screen = app.screen
                assert isinstance(screen, FeedScreen)
                tree = screen.query_one("#feed-tree", Tree)
                labels = [l for l, _ in _tree_nodes(tree)]
                assert any("Tech" in l for l in labels)
                assert any("News" in l for l in labels)
                assert all("Uncategorized" not in l for l in labels)
                tech_idx = next(i for i,l in enumerate(labels) if "Tech" in l)
                news_idx = next(i for i,l in enumerate(labels) if "News" in l)
                assert tech_idx < news_idx
                feed_labels = [l for l in labels if "LWN" in l or "Hacker" in l]
                assert "LWN" in feed_labels[0]
        asyncio.run(main())
    run()


def test_uncategorized_group_appears(state_path):
    dm = DataManager(state_path)
    dm.add_feed("https://example.com/nocat.xml")
    def run():
        app = AetherNews(data_path=state_path)
        async def main():
            async with app.run_test() as pilot:
                await pilot.pause()
                tree = app.screen.query_one("#feed-tree", Tree)
                labels = [l for l, _ in _tree_nodes(tree)]
                assert any(UNCATEGORIZED in l for l in labels)
        asyncio.run(main())
    run()


def test_feed_selection_browses_to_article_screen(state_path):
    _seed_state(state_path)
    def run():
        app = AetherNews(data_path=state_path)
        async def main():
            async with app.run_test() as pilot:
                await pilot.pause()
                tree = app.screen.query_one("#feed-tree", Tree)
                feed_node = None
                for node in tree._tree_nodes.values():
                    if isinstance(node.data, _FeedData) and node.data.url.endswith("tech.xml"):
                        feed_node = node
                        break
                assert feed_node is not None
                tree.move_cursor(feed_node)
                tree.select_node(feed_node)
                await pilot.pause()
                from aethernews.screens.article_screen import ArticleScreen
                assert isinstance(app.screen, ArticleScreen)
        asyncio.run(main())
    run()


def test_assign_category_via_dialog(state_path):
    # A single uncategorized feed — user categorizes it via the 'c' dialog.
    dm = DataManager(state_path)
    dm.add_feed("https://example.com/nocat.xml")
    dm.save_cached_result("https://example.com/nocat.xml", FeedResult(
        title="Lone Feed", articles=[_article("A1", "a1", "2026-08-13T08:00:00Z")]))
    def run():
        app = AetherNews(data_path=state_path)
        async def main():
            async with app.run_test() as pilot:
                await pilot.pause()
                from aethernews.screens.dialogs import CategoryDialog
                from aethernews.screens.feed_screen import _FeedData, _GroupData
                tree = app.screen.query_one("#feed-tree", Tree)
                # expand the (single) collapsed group so its feed is reachable
                group_node = next(
                    n for n in tree._tree_nodes.values()
                    if isinstance(n.data, _GroupData)
                )
                tree.move_cursor(group_node)
                await pilot.press("space")
                await pilot.pause()
                feed_node = next(
                    n for n in tree._tree_nodes.values()
                    if isinstance(n.data, _FeedData)
                )
                tree.move_cursor(feed_node)
                await pilot.pause()
                await pilot.press("c")
                await pilot.pause()
                assert isinstance(app.screen, CategoryDialog)
                # type a new category name and submit
                await pilot.press("G", "a", "m", "i", "n", "g")
                await pilot.press("enter")
                await pilot.pause()
                # back on feed screen; feed now categorized (persisted to disk)
                assert isinstance(app.screen, FeedScreen)
                import json
                data = json.loads(state_path.read_text(encoding="utf-8"))
                assert data["categories"]["https://example.com/nocat.xml"] == "Gaming"
                # group now shows Gaming, not Uncategorized
                labels = [l for l, _ in _tree_nodes(tree)]
                assert any("Gaming" in l for l in labels)
                assert all("Uncategorized" not in l for l in labels)
        asyncio.run(main())
    run()


def test_rename_category_via_group_node(state_path):
    _seed_state(state_path)  # Tech group with 2 feeds
    def run():
        app = AetherNews(data_path=state_path)
        async def main():
            async with app.run_test() as pilot:
                await pilot.pause()
                from aethernews.screens.dialogs import CategoryDialog
                tree = app.screen.query_one("#feed-tree", Tree)
                group_node = next(
                    n for n in tree._tree_nodes.values()
                    if isinstance(n.data, _GroupData) and n.data.category == "Tech"
                )
                tree.move_cursor(group_node)
                await pilot.pause()
                await pilot.press("c")
                await pilot.pause()
                assert isinstance(app.screen, CategoryDialog)
                # replace the current name with a new one
                inp = app.screen.query_one("#cat-input")
                inp.value = "Technology"
                await pilot.press("enter")
                await pilot.pause()
                assert isinstance(app.screen, FeedScreen)
                import json
                data = json.loads(state_path.read_text(encoding="utf-8"))
                cats = set(data["categories"].values())
                assert "Technology" in cats
                assert "Tech" not in cats
        asyncio.run(main())
    run()


def test_opening_reader_does_not_mark_read(state_path):
    # Matches AetherPod: viewing an article must not mark it read.
    dm = DataManager(state_path)
    dm.add_feed("https://example.com/t.xml")
    dm.save_cached_result("https://example.com/t.xml", FeedResult(
        title="T", articles=[_article("A1", "a1", "2026-08-13T08:00:00Z")]))
    def run():
        app = AetherNews(data_path=state_path)
        async def main():
            async with app.run_test() as pilot:
                await pilot.pause()
                from aethernews.screens.feed_screen import _FeedData, _GroupData
                tree = app.screen.query_one("#feed-tree", Tree)
                g = next(n for n in tree._tree_nodes.values()
                         if isinstance(n.data, _GroupData))
                tree.move_cursor(g)
                await pilot.press("right")  # expand
                await pilot.pause()
                f = next(n for n in tree._tree_nodes.values()
                         if isinstance(n.data, _FeedData))
                tree.move_cursor(f)
                tree.select_node(f)
                await pilot.pause()
                # open the article in the reader
                app.screen.query_one("#article-list").move_cursor(row=0)
                await pilot.press("enter")
                await pilot.pause()
                from aethernews.screens.detail_help import ReaderScreen
                assert isinstance(app.screen, ReaderScreen)
                # article must still be unread
                assert dm.is_unread("a1") is True
        asyncio.run(main())
    run()


def test_recency_unread_default_sort(state_path):
    # Recency primary (today > yesterday > older), unread tiebreak within a day.
    import datetime as dt
    dm = DataManager(state_path)
    now = dt.datetime.now(dt.timezone.utc)
    def h(n):
        return (now - dt.timedelta(hours=n)).strftime("%Y-%m-%dT%H:%M:%SZ")
    def d(n):
        return (now - dt.timedelta(days=n)).strftime("%Y-%m-%dT%H:%M:%SZ")
    dm.add_feed("https://example.com/t.xml")
    dm.set_category("https://example.com/t.xml", "Tech")
    dm.save_cached_result("https://example.com/t.xml", FeedResult(
        title="LWN", articles=[
            _article("Old unread 5d", "a1", d(5)),
            _article("Old read 4d", "a2", d(4)),
            _article("Today read 1h", "a3", h(1)),
            _article("Today unread 2h", "a4", h(2)),
            _article("Yesterday unread 30h", "a5", h(30)),
        ]))
    dm.mark_read("a2")
    dm.mark_read("a3")
    def run():
        app = AetherNews(data_path=state_path)
        async def main():
            async with app.run_test() as pilot:
                await pilot.pause()
                from aethernews.screens.feed_screen import _FeedData, _GroupData
                tree = app.screen.query_one("#feed-tree", Tree)
                g = next(n for n in tree._tree_nodes.values()
                         if isinstance(n.data, _GroupData))
                tree.move_cursor(g)
                await pilot.press("right")
                await pilot.pause()
                f = next(n for n in tree._tree_nodes.values()
                         if isinstance(n.data, _FeedData))
                tree.move_cursor(f)
                tree.select_node(f)
                await pilot.pause()
                s = app.screen
                assert s._sort_state == 0  # recency+unread default
                titles = [a.title for a in s._sorted_articles()]
                assert titles == [
                    "Today unread 2h",
                    "Today read 1h",
                    "Yesterday unread 30h",
                    "Old read 4d",
                    "Old unread 5d",
                ]
        asyncio.run(main())
    run()


def test_groups_collapsed_by_default_and_toggle(state_path):
    _seed_state(state_path)
    def run():
        app = AetherNews(data_path=state_path)
        async def main():
            async with app.run_test() as pilot:
                await pilot.pause()
                tree = app.screen.query_one("#feed-tree", Tree)
                group_nodes = [
                    node for node in tree._tree_nodes.values()
                    if isinstance(node.data, _GroupData)
                ]
                assert group_nodes, "expected at least one group node"
                # all groups start collapsed
                assert all(node.is_collapsed for node in group_nodes)
                # cursor on first group (Tech, newest) — press space to expand
                await pilot.press("space")
                await pilot.pause()
                expanded = [node for node in group_nodes if not node.is_collapsed]
                assert len(expanded) == 1
                assert any("Tech" in node.label.plain for node in expanded)
                # press space again to collapse it back
                await pilot.press("space")
                await pilot.pause()
                assert all(node.is_collapsed for node in group_nodes)
        asyncio.run(main())
    run()
