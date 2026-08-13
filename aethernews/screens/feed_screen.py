# Created: 2026-08-12
# Last Edited: 2026-08-13 13:42 CT (America/Chicago)
# Path: aethernews/screens/feed_screen.py
# Purpose: Feed overview screen — category-grouped tree, recency markers, newest-first sort.

from __future__ import annotations

import asyncio
import datetime
import logging

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.events import Key
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, Tree
from textual.widgets._tree import TreeNode

from aethernews.engine import DataManager
from aethernews.models import FeedResult
from aethernews.rss import fetch_feed_async
from aethernews.screens.article_screen import ArticleScreen
from aethernews.screens.detail_help import HelpScreen
from aethernews.screens.dialogs import AddFeedDialog, CategoryDialog, PathInputDialog
from aethernews.widgets import LoadingSpinner

logger = logging.getLogger(__name__)

UNCATEGORIZED = "Uncategorized"


class _GroupData:
    """Node payload for a category group row."""

    def __init__(self, category: str, urls: list[str]) -> None:
        self.category = category
        self.urls = urls


class _FeedData:
    """Node payload for a feed row."""

    def __init__(self, url: str) -> None:
        self.url = url


class FeedScreen(Screen):
    BINDINGS = [
        Binding("a", "add_feed", "Add Feed"),
        Binding("i", "import_opml", "Import OPML"),
        Binding("e", "export_opml", "Export OPML"),
        Binding("u", "refresh", "Refresh"),
        Binding("r", "remove_feed", "Remove"),
        Binding("s", "toggle_sort", "Sort"),
        Binding("f", "toggle_filter", "Filter"),
        Binding("c", "assign_category", "Category"),
        Binding("right", "expand_node", "Expand", show=False),
        Binding("left", "collapse_node", "Collapse", show=False),
        Binding("q", "quit", "Quit"),
        Binding("question_mark", "show_help", "Help", key_display="?"),
    ]

    def __init__(self, data_manager: DataManager) -> None:
        super().__init__()
        self._data = data_manager
        self._sort_newest: bool = True
        self._filter_query: str = ""
        self._categorize_url: str | None = None
        self._rename_category: str | None = None
        self._refresh_in_flight: set[str] = set()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="Filter feeds\u2026", id="feed-filter", classes="feed-filter")
        yield LoadingSpinner(id="feed-status")
        yield Tree("Feeds", id="feed-tree")
        yield Footer()

    async def on_mount(self) -> None:
        # Keep the hidden filter input out of the focus order (AetherPod
        # lesson: display:none widgets still capture focus on mount).
        self.query_one("#feed-filter", Input).can_focus = False
        tree = self.query_one("#feed-tree", Tree)
        tree.show_root = False
        tree.focus()
        self._render_from_cache()
        asyncio.create_task(self._refresh_feeds())

    def action_add_feed(self) -> None:
        def _on_url(url: str | None) -> None:
            if url:
                if self._data.add_feed(url):
                    self.notify("Feed added", severity="information", timeout=3)
                else:
                    self.notify("Feed already subscribed", severity="warning", timeout=3)
                asyncio.create_task(self._refresh_feeds())

        self.app.push_screen(AddFeedDialog(), _on_url)

    async def action_refresh(self) -> None:
        await self._refresh_feeds()

    def action_remove_feed(self) -> None:
        tree = self.query_one("#feed-tree", Tree)
        node = tree.cursor_node
        if node is None or not isinstance(node.data, _FeedData):
            self.notify("No feed selected", severity="warning", timeout=2)
            return
        url = node.data.url
        self._data.remove_feed(url)
        self.notify("Removed feed", severity="information", timeout=2)
        asyncio.create_task(self._refresh_feeds())

    def action_assign_category(self) -> None:
        tree = self.query_one("#feed-tree", Tree)
        node = tree.cursor_node
        if node is None or node.data is None:
            self.notify("Select a feed or category", severity="warning", timeout=2)
            return
        if isinstance(node.data, _FeedData):
            url = node.data.url
            title = self._feed_title_for(url)
            current = self._data.get_category(url)
            existing = self._data.get_categories_list()
            self._categorize_url = url
            self.app.push_screen(
                CategoryDialog(title, current, existing), self._on_category_picked
            )
        elif isinstance(node.data, _GroupData):
            category = node.data.category
            if category == UNCATEGORIZED:
                self.notify("Uncategorized has no renameable category",
                            severity="warning", timeout=2)
                return
            self._rename_category = category
            self.app.push_screen(
                CategoryDialog(
                    f"Rename \u201c{category}\u201d", category,
                    self._data.get_categories_list(),
                ),
                self._on_category_renamed,
            )

    def _on_category_picked(self, category: str | None) -> None:
        if category is None or self._categorize_url is None:
            return
        self._data.set_category(self._categorize_url, category)
        label = category or "Uncategorized"
        self.notify(f"Category: {label}", severity="information", timeout=2)
        self._render_from_cache()

    def _on_category_renamed(self, new_name: str | None) -> None:
        if new_name is None or not self._rename_category:
            return
        old = self._rename_category
        count = self._data.rename_category(old, new_name)
        label = new_name or "Uncategorized"
        self.notify(
            f"Renamed \u201c{old}\u201d \u2192 \u201c{label}\u201d ({count} feed(s))",
            severity="information", timeout=2,
        )
        self._render_from_cache()

    def action_expand_node(self) -> None:
        tree = self.query_one("#feed-tree", Tree)
        node = tree.cursor_node
        if node is not None:
            node.expand()

    def action_collapse_node(self) -> None:
        tree = self.query_one("#feed-tree", Tree)
        node = tree.cursor_node
        if node is not None:
            node.collapse()

    def action_quit(self) -> None:
        self.app.exit()

    def action_import_opml(self) -> None:
        def _on_path(path: str | None) -> None:
            if path:
                count = self._data.opml_import(path)
                if count > 0:
                    self.notify(f"Imported {count} feed(s)", severity="information", timeout=3)
                else:
                    self.notify("No new feeds found", severity="warning", timeout=3)
                asyncio.create_task(self._refresh_feeds())

        self.app.push_screen(PathInputDialog("Import OPML", "path/to/subscriptions.opml"), _on_path)

    def action_export_opml(self) -> None:
        def _on_path(path: str | None) -> None:
            if path:
                count = self._data.opml_export(path)
                if count > 0:
                    self.notify(f"Exported {count} feed(s)", severity="information", timeout=3)
                else:
                    self.notify("No feeds to export", severity="warning", timeout=3)

        self.app.push_screen(
            PathInputDialog("Export OPML", "aethernews_subscriptions.opml"), _on_path
        )

    def action_show_help(self) -> None:
        self.app.push_screen(HelpScreen(screen_name="Feed"))

    def action_toggle_sort(self) -> None:
        self._sort_newest = not self._sort_newest
        label = "newest-first" if self._sort_newest else "subscribe order"
        self.notify(f"Feeds sorted: {label}", severity="information", timeout=2)
        self._render_from_cache()

    def action_toggle_filter(self) -> None:
        filt = self.query_one("#feed-filter", Input)
        if filt.has_class("visible"):
            self._close_filter()
        else:
            filt.add_class("visible")
            filt.can_focus = True
            filt.focus()

    def _close_filter(self) -> None:
        filt = self.query_one("#feed-filter", Input)
        filt.remove_class("visible")
        filt.can_focus = False
        self._filter_query = ""
        filt.value = ""
        self.query_one("#feed-tree", Tree).focus()
        self._render_from_cache()
        self.notify("Filter cleared", severity="information", timeout=1)

    def on_key(self, event: Key) -> None:
        if event.key == "escape":
            filt = self.query_one("#feed-filter", Input)
            if filt.has_class("visible"):
                self._close_filter()
                event.stop()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "feed-filter":
            return
        self._filter_query = event.value.strip().lower()
        self._render_from_cache()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "feed-filter":
            self.action_toggle_filter()

    def _feed_title_for(self, url: str) -> str:
        cached = self._data.get_cached_result(url)
        if cached and cached.title:
            return cached.title
        return url

    def _updated_ts(self, url: str) -> datetime.datetime:
        """Comparable timestamp for a feed (newest article or check time)."""
        updated = self._data.feed_updated(url)
        if updated is None:
            return datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
        return updated

    def _feed_urls(self) -> list[str]:
        """All feed URLs, filtered by name query, sorted by recency or subscribe order."""
        urls = self._data.get_feeds()
        if self._filter_query:
            urls = [
                u for u in urls
                if self._filter_query in self._feed_title_for(u).lower()
            ]
        if self._sort_newest:
            urls = sorted(urls, key=self._updated_ts, reverse=True)
        return urls

    def _grouped_urls(self, urls: list[str]) -> list[tuple[str, list[str]]]:
        """Partition feed URLs into (category, [urls]) groups, newest first.

        The "Uncategorized" group always sorts last.  Groups without any
        feed after filtering are dropped.
        """
        by_cat: dict[str, list[str]] = {}
        for u in urls:
            cat = self._data.get_category(u) or UNCATEGORIZED
            by_cat.setdefault(cat, []).append(u)

        def _latest(group_urls: list[str]) -> datetime.datetime:
            return max((self._updated_ts(u) for u in group_urls), default=(
                datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)))

        groups = sorted(by_cat.items(), key=lambda kv: _latest(kv[1]), reverse=True)
        if UNCATEGORIZED in by_cat:
            groups = [
                (c, us) for c, us in groups if c != UNCATEGORIZED
            ] + [(UNCATEGORIZED, by_cat[UNCATEGORIZED])]
        return groups

    def _group_label(self, category: str, urls: list[str]) -> Text:
        n_feeds = len(urls)
        n_unread = sum(self._data.unread_by_feed(u) for u in urls)
        recent = any(self._data.recently_updated(u) for u in urls)
        label = Text()
        if recent:
            label.append("● ", style="bold cyan")
        label.append(f"{category}", style="bold")
        label.append(
            f"  ({n_feeds} feed{'s' if n_feeds != 1 else ''}"
            f", {n_unread} unread)",
            style="dim",
        )
        return label

    def _feed_label(self, url: str) -> Text:
        cached = self._data.get_cached_result(url)
        label = Text()
        if cached is not None:
            unread = self._data.unread_by_feed(url)
            recent = self._data.recently_updated(url)
            if recent:
                label.append("● ", style="bold cyan")
            title_style = "bold cyan" if (recent and unread) else (
                "bold" if unread else "")
            label.append(cached.title, style=title_style or None)
            label.append(
                f"  ({len(cached.articles)}, {unread} unread)",
                style="dim",
            )
        else:
            label.append(f"  {url}  (waiting...)", style="dim")
        return label

    def _render_from_cache(self) -> None:
        tree = self.query_one("#feed-tree", Tree)
        tree.clear()
        urls = self._feed_urls()
        if not urls:
            msg = "No feeds \u2014 press 'a' to add one"
            if self._filter_query:
                msg = f"No feeds match \u201c{self._filter_query}\u201d \u2014 Esc to clear"
            self._set_status(msg)
            return

        for category, group_urls in self._grouped_urls(urls):
            group_node = tree.root.add(self._group_label(category, group_urls),
                                       _GroupData(category, group_urls),
                                       expand=False)
            for u in group_urls:
                group_node.add_leaf(self._feed_label(u), _FeedData(u))

        if urls:
            self._set_status(
                f"{len(urls)} feed{'s' if len(urls) != 1 else ''}"
                " \u2014 'a' to add, Enter to browse"
            )

    async def _refresh_feeds(self) -> None:
        urls = self._feed_urls()
        if not urls:
            return

        ttl = self._data.get_cache_ttl()
        to_fetch = [
            url for url in urls
            if not self._data.is_cache_fresh(url, max_age=ttl)
        ]

        if to_fetch:
            self._start_spinner(
                f"Refreshing {len(to_fetch)} of {len(urls)} feed(s)..."
            )
        else:
            self._set_status(
                f"{len(urls)} feed(s) \u2014 all fresh, no refresh needed"
            )

        tasks = []
        for url in to_fetch:
            headers = self._data.get_feed_headers(url)
            tasks.append(
                fetch_feed_async(url,
                                 etag=headers.get("etag", ""),
                                 last_modified=headers.get("last_modified", ""))
            )
        results = await asyncio.gather(*tasks, return_exceptions=True)
        fetched: dict[str, FeedResult | Exception] = dict(zip(to_fetch, results))

        tree = self.query_one("#feed-tree", Tree)
        tree.clear()
        for category, group_urls in self._grouped_urls(urls):
            group_node = tree.root.add(self._group_label(category, group_urls),
                                       _GroupData(category, group_urls),
                                       expand=False)
            for u in group_urls:
                result = fetched.get(u)
                error_text: str | None = None
                if isinstance(result, Exception):
                    logger.warning("Feed fetch exception for %s: %s", u, result)
                    error_text = str(result)
                elif result is not None:
                    if result.not_modified:
                        self._data.touch_cache(u)
                    elif result.error:
                        error_text = result.error
                    else:
                        if result.etag or result.last_modified:
                            self._data.save_feed_headers(
                                u, result.etag, result.last_modified)
                        self._data.save_cached_result(u, result)

                label = self._feed_label(u)
                if error_text:
                    label.append(
                        f"\u2717 {error_text}",
                        style="bold red",
                    )
                group_node.add_leaf(label, _FeedData(u))

        n = len(urls)
        self._set_status(
            f"{n} feed{'s' if n != 1 else ''} \u2014 'a' to add, Enter to browse"
        )

    def _start_spinner(self, msg: str) -> None:
        try:
            self.query_one("#feed-status", LoadingSpinner).start(msg)
        except Exception as exc:
            logger.debug("Feed status widget not ready: %s", exc)

    def _set_status(self, msg: str) -> None:
        try:
            spinner = self.query_one("#feed-status", LoadingSpinner)
            spinner.stop()
            spinner.update(msg)
        except Exception as exc:
            logger.debug("Feed status widget not ready: %s", exc)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        node: TreeNode | None = event.node
        if node is None or node.data is None:
            return
        data = node.data
        if isinstance(data, _GroupData):
            node.toggle()
            return
        if isinstance(data, _FeedData):
            url = data.url
            cached = self._data.get_cached_result(url)
            if cached is not None and cached.error:
                self._set_status(f"\u2717 {cached.error}")
                self.notify(f"Cannot browse: {cached.error}", severity="error", timeout=4)
                return
            result = cached or FeedResult(title=url, articles=[])
            self.app.push_screen(ArticleScreen(result, url, self._data))
            self._maybe_refresh_selected(url)

    def _maybe_refresh_selected(self, url: str) -> None:
        """Refresh a single feed in the background if its cache is stale.

        Skips feeds that are fresh (within the TTL) and feeds that already
        have a fetch in flight, then notifies any open ``ArticleScreen``
        for the feed to re-render once the fetch completes.
        """
        if self._data.is_cache_fresh(url):
            return
        if url in self._refresh_in_flight:
            return
        self._refresh_in_flight.add(url)

        async def _task() -> None:
            try:
                headers = self._data.get_feed_headers(url)
                result = await fetch_feed_async(
                    url,
                    etag=headers.get("etag", ""),
                    last_modified=headers.get("last_modified", ""),
                )
                if result.etag or result.last_modified:
                    self._data.save_feed_headers(url, result.etag, result.last_modified)
                if result.not_modified:
                    self._data.touch_cache(url)
                self._data.save_cached_result(url, result)
                if result.error is None:
                    for screen in self.app.screen_stack:
                        if isinstance(screen, ArticleScreen) and screen._feed_url == url:
                            screen.reload_from_cache()
            except Exception as exc:
                logger.warning("Background refresh failed for %s: %s", url, exc)
            finally:
                self._refresh_in_flight.discard(url)

        asyncio.create_task(_task())
