# Created: 2026-08-12
# Last Edited: 2026-08-13 15:43 CT (America/Chicago)
# Path: aethernews/app.py
# Purpose: Main Textual TUI application — screen orchestration, CSS, theme toggle.

from __future__ import annotations

import logging
from pathlib import Path

from textual.app import App
from textual.binding import Binding

from aethernews import __version__
from aethernews.engine import DataManager
from aethernews.screens.article_screen import ArticleScreen
from aethernews.screens.splash import SplashScreen
from aethernews.theme import THEMES

logger = logging.getLogger(__name__)


class AetherNews(App):
    """Root Textual application for the AetherNews RSS reader.

    Registers custom dark/light themes on mount and pushes the feed
    subscription screen.  App-level keybinding: ``t`` toggles dark/light.
    """

    TITLE = f"AetherNews - v{__version__}"
    SUB_TITLE = ""
    ALLOW_SELECT = False

    BINDINGS = [
        Binding("t", "toggle_theme", "Theme"),
    ]

    CSS = """
    Screen {
        background: $surface;
    }

    Tree {
        height: 1fr;
        margin: 0 1;
    }

    Tree > .tree--cursor {
        background: $accent 20%;
        text-style: bold;
    }

    /* ── Feed filter input ─────────────────────────────── */
    #feed-filter {
        display: none;
        margin: 0 1;
    }

    #feed-filter.visible {
        display: block;
    }

    DataTable {
        height: 1fr;
        margin: 0 1;
    }

    DataTable > .datatable--header {
        background: $panel;
        color: $text-muted;
        text-style: bold;
        height: 1;
    }

    DataTable > .datatable--even-row {
        background: $surface;
    }

    DataTable > .datatable--odd-row {
        background: $panel;
    }

    DataTable > .datatable--cursor {
        background: $accent 25%;
    }

    .status {
        height: 1;
        background: $panel;
        color: $text-muted;
        padding: 0 1;
    }

    /* ── Dialogs ──────────────────────────────────────── */
    AddFeedDialog, PathInputDialog, CategoryDialog {
        align: center middle;
        background: $surface 85%;
    }

    AddFeedDialog .dialog-title, PathInputDialog .dialog-title,
    CategoryDialog .dialog-title {
        text-style: bold;
        text-align: center;
        width: 100%;
        padding-bottom: 1;
        margin-top: 1;
    }

    AddFeedDialog Input, PathInputDialog Input, CategoryDialog Input {
        width: 50;
    }

    AddFeedDialog Button, PathInputDialog Button, CategoryDialog Button {
        width: 16;
        margin-top: 1;
    }

    AddFeedDialog .dialog-error, PathInputDialog .dialog-error,
    CategoryDialog .dialog-error {
        height: 1;
        text-align: center;
        width: 100%;
    }

    CategoryDialog Select {
        width: 50;
        margin-top: 1;
    }

    /* ── Splash Screen ─────────────────────────────────── */
    SplashScreen {
        align: center middle;
        background: $surface;
    }

    SplashScreen #splash-content {
        width: auto;
        height: auto;
        margin: 1 2;
    }

    SplashScreen #splash-hint {
        dock: bottom;
        width: 100%;
        text-align: center;
        color: $text-muted;
        padding-bottom: 1;
    }

    /* ── Reader Screen ─────────────────────────────────── */
    ReaderScreen {
        align: center middle;
        background: $surface 95%;
    }

    ReaderScreen .dialog-title {
        text-style: bold;
        text-align: center;
        width: 100%;
        padding-bottom: 1;
    }

    ReaderScreen #reader-body {
        width: 1fr;
        height: 1fr;
        margin: 0 4;
    }

    ReaderScreen #reader-body-content {
        width: 100%;
        padding: 0 2 1 2;
    }

    /* ── Help Screen ───────────────────────────────────── */
    HelpScreen {
        align: center middle;
        background: $surface 90%;
    }

    HelpScreen .dialog-title {
        text-style: bold;
        text-align: center;
        width: 100%;
        padding-bottom: 1;
    }

    HelpScreen #help-content {
        width: 60;
        padding: 0 2 1 2;
    }

    HelpScreen #help-footer {
        width: 100%;
        text-align: center;
    }

    HelpScreen #help-stack {
        width: 100%;
        text-align: center;
        color: $text-muted;
        padding-bottom: 1;
    }
    """

    def __init__(self, data_path: str | Path | None = None) -> None:
        super().__init__()
        self._data = DataManager(data_path)

    def on_mount(self) -> None:
        for theme in THEMES.values():
            self.register_theme(theme)
        self.theme = "aethernews-dark"
        n_feeds = len(self._data.get_feeds())
        n_unread = self._data.total_unread()
        n_categories = len(self._data.get_categories_list())
        logger.info("AetherNews starting — %d feed(s), %d unread", n_feeds, n_unread)
        self.push_screen(
            SplashScreen(self._data, n_feeds, n_unread, n_categories)
        )
        self.set_interval(1, self._poll_article_status)

    def on_unmount(self) -> None:
        self._data.save()

    def action_toggle_theme(self) -> None:
        self.theme = "aethernews-light" if self.theme == "aethernews-dark" else "aethernews-dark"
        name = self.theme.replace("aethernews-", "").title()
        self.notify(f"Theme: {name}", severity="information", timeout=1)

    def _poll_article_status(self) -> None:
        """1-second poll — keep unread counts + read styling fresh.

        Article screens don't need per-second updates unless read state
        changed (e.g. ReaderScreen marked something read); re-render only
        when the unread count actually moved.
        """
        for screen in self.screen_stack:
            if isinstance(screen, ArticleScreen):
                before = screen._last_unread
                current = sum(
                    1 for a in screen._feed.articles
                    if self._data.is_unread(a.article_id or "")
                )
                if current != before:
                    screen._last_unread = current
                    screen._populate()
