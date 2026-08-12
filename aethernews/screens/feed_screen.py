# Created: 2026-08-12
# Last Edited: 2026-08-12 18:02 CT (America/Chicago)
# Path: aethernews/screens/feed_screen.py
# Purpose: Feed subscription list screen — main entry screen for AetherNews.

from __future__ import annotations

import asyncio
import logging

from textual.app import ComposeResult
from textual.binding import Binding
from textual.events import Key
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, Label, ListItem, ListView

from aethernews.engine import DataManager
from aethernews.models import FeedResult
from aethernews.rss import fetch_feed_async
from aethernews.screens.article_screen import ArticleScreen
from aethernews.screens.detail_help import HelpScreen
from aethernews.screens.dialogs import AddFeedDialog, PathInputDialog
from aethernews.widgets import LoadingSpinner

logger = logging.getLogger(__name__)


class FeedScreen(Screen):
    BINDINGS = [
        Binding("a", "add_feed", "Add Feed"),
        Binding("i", "import_opml", "Import OPML"),
        Binding("e", "export_opml", "Export OPML"),
        Binding("u", "refresh", "Refresh"),
        Binding("r", "remove_feed", "Remove"),
        Binding("s", "toggle_sort", "Sort A-Z"),
        Binding("f", "toggle_filter", "Filter"),
        Binding("c", "cycle_category_filter", "Category"),
        Binding("q", "quit", "Quit"),
        Binding("question_mark", "show_help", "Help", key_display="?"),
    ]

    def __init__(self, data_manager: DataManager) -> None:
        super().__init__()
        self._data = data_manager
        self._sort_asc: bool | None = None
        self._filter_query: str = ""
        self._category_filter: str = ""
        self._refresh_in_flight: set[str] = set()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="Filter feeds\u2026", id="feed-filter", classes="feed-filter")
        yield LoadingSpinner(id="feed-status")
        yield ListView(id="feed-list")
        yield Footer()

    async def on_mount(self) -> None:
        # Keep the hidden filter input out of the focus order (AetherPod
        # lesson: display:none widgets still capture focus on mount).
        self.query_one("#feed-filter", Input).can_focus = False
        self.query_one("#feed-list", ListView).focus()
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
        feed_list = self.query_one("#feed-list", ListView)
        if feed_list.index is None:
            self.notify("No feed selected", severity="warning", timeout=2)
            return
        item = feed_list.children[feed_list.index]
        url: str | None = getattr(item, "_feed_url", None)
        if url:
            self._data.remove_feed(url)
            self.notify("Removed feed", severity="information", timeout=2)
            asyncio.create_task(self._refresh_feeds())

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
        if self._sort_asc is None:
            self._sort_asc = True
        elif self._sort_asc:
            self._sort_asc = False
        else:
            self._sort_asc = None
        label = {None: "subscribe order", True: "A\u2192Z", False: "Z\u2192A"}[self._sort_asc]
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

    def action_cycle_category_filter(self) -> None:
        cats = self._data.get_categories_list()
        if not cats:
            self.notify("No categories set", severity="warning", timeout=2)
            return
        if self._category_filter:
            idx = cats.index(self._category_filter)
            self._category_filter = cats[(idx + 1) % len(cats)] or ""
        else:
            self._category_filter = cats[0]
        if not self._category_filter:
            self.notify("Category filter: all", severity="information", timeout=1)
        else:
            self.notify(
                f"Category filter: {self._category_filter}",
                severity="information",
                timeout=1,
            )
        self._render_from_cache()

    def _close_filter(self) -> None:
        filt = self.query_one("#feed-filter", Input)
        filt.remove_class("visible")
        filt.can_focus = False
        self._filter_query = ""
        filt.value = ""
        self.query_one("#feed-list", ListView).focus()
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

    def _display_order(self, urls: list[str]) -> list[str]:
        """Apply category filter + name filter + sort to the raw feed URL list."""
        if self._category_filter:
            urls = [
                u for u in urls
                if self._data.get_category(u) == self._category_filter
            ]
        if self._filter_query:
            urls = [
                u for u in urls
                if self._filter_query in self._feed_title_for(u).lower()
            ]
        if self._sort_asc is not None:
            urls = sorted(urls, key=self._feed_title_for, reverse=not self._sort_asc)
        return urls

    def _render_from_cache(self) -> None:
        urls = self._display_order(self._data.get_feeds())
        feed_list = self.query_one("#feed-list", ListView)
        try:
            feed_list.clear()
        except ValueError:
            logger.debug("Ignored ListView hover race during clear")

        if not urls:
            msg = "No feeds \u2014 press 'a' to add one"
            if self._category_filter:
                msg = f"No feeds in category \u201c{self._category_filter}\u201d"
            elif self._filter_query:
                msg = f"No feeds match \u201c{self._filter_query}\u201d \u2014 Esc to clear"
            feed_list.append(ListItem(Label(msg)))
            self._set_status(msg)
            return

        for idx, url in enumerate(urls):
            cached = self._data.get_cached_result(url)
            item = ListItem()
            if idx % 2 == 1:
                item.add_class("zebra")
            item._feed_url = url
            item._feed_result = cached
            if cached is not None:
                total = len(cached.articles)
                unread = self._data.unread_by_feed(url)
                cat = self._data.get_category(url)
                cat_str = f"  [{cat}]" if cat else ""
                label = Label(
                    f"{cached.title}{cat_str}  ({total}, {unread} unread)"
                )
            else:
                label = Label(f"  {url}  (waiting...)")
            item.compose_add_child(label)
            feed_list.append(item)

        if urls:
            self._start_spinner(
                f"{len(urls)} feed{'s' if len(urls) != 1 else ''}"
                " \u2014 refreshing..."
            )

    async def _refresh_feeds(self) -> None:
        urls = self._display_order(self._data.get_feeds())
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

        feed_list = self.query_one("#feed-list", ListView)
        try:
            feed_list.clear()
        except ValueError:
            logger.debug("Ignored ListView hover race during refresh")

        for idx, url in enumerate(urls):
            item = ListItem()
            if idx % 2 == 1:
                item.add_class("zebra")
            item._feed_url = url

            result = fetched.get(url)
            if result is None:
                cached = self._data.get_cached_result(url)
                item._feed_result = cached
                label = self._label_for(url, cached)
            elif isinstance(result, Exception):
                logger.warning("Feed fetch exception for %s: %s", url, result)
                cached = self._data.get_cached_result(url)
                item._feed_result = cached
                label = self._label_for(url, cached, f"\u2717 {url} \u2014 {result}")
            elif result.not_modified:
                self._data.touch_cache(url)
                cached = self._data.get_cached_result(url)
                item._feed_result = cached
                label = self._label_for(url, cached)
            elif result.error:
                cached = self._data.get_cached_result(url)
                item._feed_result = cached
                label = self._label_for(url, cached, f"\u2717 {url} \u2014 {result.error}")
            else:
                if result.etag or result.last_modified:
                    self._data.save_feed_headers(url, result.etag, result.last_modified)
                self._data.save_cached_result(url, result)
                item._feed_result = result
                label = self._label_for(url, result)

            item.compose_add_child(Label(label))
            feed_list.append(item)

        n = len(urls)
        self._set_status(f"{n} feed{'s' if n != 1 else ''} \u2014 'a' to add, Enter to browse")

    def _label_for(
        self, url: str, cached: FeedResult | None, fallback: str | None = None
    ) -> str:
        """Build the feed row label with unread badge + category."""
        if cached:
            unread = self._data.unread_by_feed(url)
            cat = self._data.get_category(url)
            cat_str = f"  [{cat}]" if cat else ""
            return f"{cached.title}{cat_str}  ({len(cached.articles)}, {unread} unread)"
        if fallback:
            return fallback
        return f"  {url}"

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

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        feed_list = self.query_one("#feed-list", ListView)
        if item not in feed_list._nodes:
            # AetherPod lesson: guard against stale selections from a
            # background refresh that rebuilt the ListView mid-click.
            logger.debug("Ignoring selection for stale ListItem")
            return
        result: FeedResult | None = getattr(item, "_feed_result", None)
        url: str | None = getattr(item, "_feed_url", None)
        if result is not None and result.error:
            self._set_status(f"\u2717 {result.error}")
            self.notify(f"Cannot browse: {result.error}", severity="error", timeout=4)
            return

        if url is not None:
            if result is None:
                result = FeedResult(title=url, articles=[])
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
