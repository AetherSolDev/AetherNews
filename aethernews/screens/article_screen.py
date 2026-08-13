# Created: 2026-08-12
# Last Edited: 2026-08-13 15:26 CT (America/Chicago)
# Path: aethernews/screens/article_screen.py
# Purpose: Article browser for a single feed — read/unread, star, sort, reader.

from __future__ import annotations

import logging

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header

from aethernews.engine import DataManager
from aethernews.models import Article, FeedResult
from aethernews.rss import fetch_feed_async
from aethernews.screens.detail_help import HelpScreen, NextUnreadRequested, ReaderScreen
from aethernews.screens.helpers import day_bucket, format_date, is_recent, parse_date
from aethernews.widgets import LoadingSpinner

logger = logging.getLogger(__name__)


class ArticleScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("u", "refresh", "Refresh"),
        Binding("enter", "open_article", "Read", priority=True),
        Binding("n", "next_unread", "Next unread"),
        Binding("space", "toggle_read", "Read/Unread"),
        Binding("m", "toggle_read", "Mark"),
        Binding("shift+m", "mark_all_unread", "All Unread", key_display="M"),
        Binding("asterisk", "toggle_star", "Star", key_display="*"),
        Binding("s", "toggle_sort", "Sort"),
        Binding("t", "toggle_theme", "Theme"),
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("q", "quit", "Quit"),
        Binding("question_mark", "show_help", "Help", key_display="?"),
    ]

    def action_cursor_up(self) -> None:
        table = self.query_one("#article-list", DataTable)
        if table.cursor_row is not None and table.cursor_row > 0:
            table.move_cursor(row=table.cursor_row - 1)

    def action_cursor_down(self) -> None:
        table = self.query_one("#article-list", DataTable)
        if table.cursor_row is not None and table.cursor_row < len(table.rows) - 1:
            table.move_cursor(row=table.cursor_row + 1)

    def __init__(
        self,
        feed_result: FeedResult,
        feed_url: str | None,
        data_manager: DataManager,
    ) -> None:
        super().__init__()
        self._feed = feed_result
        self._feed_url = feed_url or feed_result.title
        self._data = data_manager
        self._show_unread_only = False
        self._sort_state = 0  # recency+unread is the default
        self._last_unread = 0
        self._row_keys: dict[str, str] = {}
        self._articles_by_row: dict[str, Article] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        yield LoadingSpinner(id="article-status")
        yield DataTable(id="article-list")
        yield Footer()

    async def on_mount(self) -> None:
        table = self.query_one("#article-list", DataTable)
        table.add_column("Status", width=8)
        table.add_column("Title", width=54)
        table.add_column("Date", width=12)
        table.cursor_type = "row"
        table.zebra_stripes = True
        self._populate()
        table.focus()

    def action_back(self) -> None:
        self.app.pop_screen()

    async def action_refresh(self) -> None:
        self._set_status("Full refresh ...")
        headers = self._data.get_feed_headers(self._feed_url)
        result = await fetch_feed_async(self._feed_url,
                                        etag=headers.get("etag", ""),
                                        last_modified=headers.get("last_modified", ""))
        if result.error:
            self.notify(f"Refresh failed: {result.error}", severity="error", timeout=4)
            self._set_status("Refresh failed")
            return
        if result.not_modified:
            self.notify("Feed unchanged", severity="information", timeout=2)
            self._set_status("Feed unchanged")
            return
        if result.etag or result.last_modified:
            self._data.save_feed_headers(self._feed_url, result.etag, result.last_modified)
        self._data.save_cached_result(self._feed_url, result)
        self._feed = self._data.get_cached_result(self._feed_url) or result
        self._populate()
        self.notify("Feed refreshed", severity="information", timeout=2)

    def reload_from_cache(self) -> None:
        """Re-read this feed's cached result and re-render.

        Called by ``FeedScreen`` after a background single-feed refresh
        triggered by browsing into this screen.
        """
        cached = self._data.get_cached_result(self._feed_url)
        if cached is None or not cached.articles:
            return
        self._feed = cached
        self._populate()

    def action_toggle_read(self) -> None:
        article = self._selected_article()
        if not article:
            return
        now_unread = self._data.toggle_read(article.article_id or "")
        self.notify(
            "Marked unread" if now_unread else "Marked read",
            severity="information", timeout=2,
        )
        self._update_row(article)
        self._update_status_bar()

    def action_mark_all_unread(self) -> None:
        count = self._data.mark_all_unread(self._feed_url)
        self.notify(
            f"Marked {count} article(s) unread",
            severity="information", timeout=2,
        )
        self._populate()

    def action_toggle_star(self) -> None:
        article = self._selected_article()
        if not article:
            return
        now_starred = self._data.toggle_starred(article.article_id or "")
        self.notify("Starred ★" if now_starred else "Unstarred", severity="information", timeout=1)
        self._update_row(article)

    def action_toggle_sort(self) -> None:
        self._sort_state = (self._sort_state + 1) % 3
        labels = {0: "recency+unread", 1: "newest-first", 2: "A\u2192Z"}
        self.notify(f"Sort: {labels[self._sort_state]}", severity="information", timeout=1)
        self._populate()

    def action_open_article(self) -> None:
        article = self._selected_article()
        if not article:
            return
        # Matches AetherPod: opening an article does NOT mark it read.
        # Only an explicit space/m toggle does.
        self.app.push_screen(ReaderScreen(article, self._data))
        self._update_status_bar()

    def action_next_unread(self) -> None:
        table = self.query_one("#article-list", DataTable)
        cur = table.cursor_row
        start = (cur + 1) if cur is not None else 0
        n = len(self._articles_by_row)
        for offset in range(n):
            idx = (start + offset) % n
            row_key = table.ordered_rows[idx].key
            article = self._articles_by_row.get(row_key)
            if article and self._data.is_unread(article.article_id or ""):
                table.move_cursor(row=idx)
                self.notify("Next unread", severity="information", timeout=1)
                return
        self.notify("No unread articles", severity="information", timeout=2)

    def on_next_unread_requested(
        self, event: NextUnreadRequested
    ) -> None:
        """Jump to the next unread when the reader asks (bubbled from App)."""
        self.action_next_unread()

    def _selected_article(self) -> Article | None:
        table = self.query_one("#article-list", DataTable)
        cursor_row = table.cursor_row
        if cursor_row is None:
            self.notify("No article selected", severity="warning", timeout=2)
            return None
        row_key = table.ordered_rows[cursor_row].key
        article = self._articles_by_row.get(row_key)
        if not article:
            self._set_status("No article data")
            return None
        return article

    def _sorted_articles(self) -> list[Article]:
        if self._sort_state == 0:
            # Recency primary, unread tiebreak: today > yesterday > older,
            # and within the same day unread floats above read.
            def key(a: Article):
                dt = parse_date(a.published)
                ts = dt.timestamp() if dt else 0.0
                return (
                    day_bucket(a.published),
                    0 if self._data.is_unread(a.article_id or "") else 1,
                    -ts,
                )
            return sorted(self._feed.articles, key=key)
        if self._sort_state == 1:
            return sorted(
                self._feed.articles,
                key=lambda a: a.published or "",
                reverse=True,
            )
        return sorted(self._feed.articles, key=lambda a: (a.title or "").lower())

    def _populate(self) -> None:
        table = self.query_one("#article-list", DataTable)
        if not table.ordered_columns:
            return
        self._row_keys.clear()
        self._articles_by_row.clear()
        table.clear()

        articles = self._sorted_articles()
        if self._show_unread_only:
            articles = [a for a in articles if self._data.is_unread(a.article_id or "")]
        self._last_unread = sum(
            1 for a in self._feed.articles if self._data.is_unread(a.article_id or "")
        )

        for article in articles:
            status, title, date = self._build_row_cells(article)
            row_key = table.add_row(status, title, date)
            aid = article.article_id or ""
            if aid:
                self._row_keys[aid] = row_key
            self._articles_by_row[row_key] = article

        if articles:
            table.move_cursor(row=0)

        self._update_status_bar()

    def _build_row_cells(self, article: Article) -> tuple:
        aid = article.article_id or ""
        unread = self._data.is_unread(aid)
        starred = self._data.is_starred(aid)

        status = Text()
        status.append("[", style="dim")
        if starred:
            status.append("★", style="bold yellow")
        elif unread:
            status.append(" ", style="dim")
        else:
            status.append("\u2713", style="dim")
        status.append("]", style="dim")

        title = (article.title[:51] + "\u2026") if len(article.title) > 51 else article.title
        if unread:
            unread_color = self.app.get_theme(self.app.theme).variables.get(
                "unread", "cyan")
            title_text = Text(title, style=f"bold {unread_color}")
        else:
            title_text = Text(title, style="dim")

        if is_recent(article.published):
            date_style = "bold cyan"
        else:
            date_style = "dim"
        date_text = Text(format_date(article.published), style=date_style)

        return (status, title_text, date_text)

    def _update_row(self, article: Article) -> None:
        aid = article.article_id or ""
        row_key = self._row_keys.get(aid)
        if row_key is None:
            return
        status, title, date = self._build_row_cells(article)
        table = self.query_one("#article-list", DataTable)
        try:
            table.update_cell(row_key, "Status", status)
            table.update_cell(row_key, "Title", title)
            table.update_cell(row_key, "Date", date)
            table.refresh()
        except Exception as exc:
            logger.debug("Could not refresh row after toggle: %s", exc)

    def _update_status_bar(self) -> None:
        total = len(self._feed.articles)
        unread = sum(
            1 for a in self._feed.articles if self._data.is_unread(a.article_id or "")
        )
        starred = sum(
            1 for a in self._feed.articles if self._data.is_starred(a.article_id or "")
        )
        sort_labels = {0: "recency+unread", 1: "newest", 2: "A-Z"}
        filter_label = " [unread]" if self._show_unread_only else ""

        t = Text()
        t.append(f" {total} articles", style="bold")
        if unread:
            t.append(f"  \u25cb{unread}", style="bold cyan")
        if starred:
            t.append(f"  \u2605{starred}", style="bold yellow")
        t.append(" \u2502", style="dim")
        t.append(f" {self._feed.title}", style="bold")
        t.append(" \u2502", style="dim")
        t.append(f" sort:{sort_labels[self._sort_state]}", style="dim")
        t.append(" \u2502", style="dim")
        t.append(f" ? help{filter_label}", style="dim")
        self._set_status(t)

    def _set_status(self, msg: str | Text) -> None:
        try:
            spinner = self.query_one("#article-status", LoadingSpinner)
            spinner.stop()
            spinner.update(msg)
        except Exception as exc:
            logger.debug("Article status widget not ready: %s", exc)

    def action_show_help(self) -> None:
        self.app.push_screen(HelpScreen(screen_name="Article"))

    def action_quit(self) -> None:
        self.app.exit()
