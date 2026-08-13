# Created: 2026-08-13
# Last Edited: 2026-08-13 15:47 CT (America/Chicago)
# Path: aethernews/screens/splash.py
# Purpose: Startup splash screen — auto-dismisses after 4s or any key.

from __future__ import annotations

from textual.app import ComposeResult
from textual.events import Key
from textual.screen import Screen
from textual.widgets import Label, Static

from aethernews.engine import DataManager
from aethernews.splash import SplashRenderable


class SplashScreen(Screen):
    def __init__(
        self, data_manager: DataManager, n_feeds: int, n_unread: int, n_categories: int
    ) -> None:
        super().__init__()
        self._data = data_manager
        self._n_feeds = n_feeds
        self._n_unread = n_unread
        self._n_categories = n_categories
        self._timer = None
        self._dismissed = False

    def compose(self) -> ComposeResult:
        splash = SplashRenderable(self._n_feeds, self._n_unread, self._n_categories)
        yield Static(splash, id="splash-content")
        yield Label("  Press any key or wait\u2026  ", id="splash-hint")

    def on_mount(self) -> None:
        self.title = ""
        self._timer = self.set_timer(4, self._auto_dismiss)

    def on_key(self, event: Key) -> None:
        self.action_dismiss()

    def action_dismiss(self) -> None:
        if self._dismissed:
            return
        self._dismissed = True
        if self._timer is not None:
            self._timer.reset()
            self._timer = None
        self.app.pop_screen()
        from aethernews.screens.feed_screen import FeedScreen

        self.app.push_screen(FeedScreen(self._data))

    def _auto_dismiss(self) -> None:
        self.action_dismiss()
