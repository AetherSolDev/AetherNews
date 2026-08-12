# Created: 2026-08-12
# Last Edited: 2026-08-12 17:40 CT (America/Chicago)
# Path: aethernews/widgets.py
# Purpose: Reusable Textual widgets for AetherNews — spinner, status bar.

from __future__ import annotations

import logging

from rich.text import Text
from textual.widgets import Static

logger = logging.getLogger(__name__)

SPINNER_CHARS = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


class LoadingSpinner(Static):
    """An animated loading spinner using braille characters.

    Cycles through *SPINNER_CHARS* at the configured interval.
    Call ``start()`` / ``stop()`` to control animation.
    Displays *message* text after the spinner (e.g. "Refreshing…").
    """

    DEFAULT_CSS = """
    LoadingSpinner {
        height: 1;
    }
    """

    def __init__(self, message: str = "", interval: float = 0.12, **kwargs) -> None:
        super().__init__(**kwargs)
        self._message = message
        self._interval = interval
        self._timer = None

    def start(self, message: str = "") -> None:
        """Begin the spinner animation."""
        if message:
            self._message = message
        if self._timer is not None:
            self._timer.stop()
        self._index = 0
        self._timer = self.set_interval(self._interval, self._tick)
        self._tick()

    def stop(self) -> None:
        """Stop the spinner and clear it."""
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        self.update("")

    def update_message(self, message: str) -> None:
        """Change the message without restarting the spinner."""
        self._message = message

    def _tick(self) -> None:
        char = SPINNER_CHARS[self._index % len(SPINNER_CHARS)]
        self._index += 1
        t = Text()
        t.append(char, style="bold cyan")
        if self._message:
            t.append(f" {self._message}", style="dim")
        self.update(t)
