# Created: 2026-08-12
# Last Edited: 2026-08-12 17:40 CT (America/Chicago)
# Path: aethernews/screens/dialogs.py
# Purpose: Input dialogs — AddFeedDialog, PathInputDialog.

from __future__ import annotations

import re

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Button, Input, Static


class AddFeedDialog(Screen[str | None]):
    """Modal dialog for entering a feed URL."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        yield Static("", id="dialog-box")
        yield Static("Add Feed URL", classes="dialog-title")
        yield Input(placeholder="https://example.com/feed.xml", id="feed-url-input")
        yield Static("", id="feed-url-error", classes="dialog-error")
        yield Button("Add", id="add-feed-btn", variant="primary")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._submit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self._submit()

    def _validate_url(self, url: str) -> str | None:
        if not url:
            return "Please enter a URL"
        if not re.match(r'^https?://', url):
            return "URL must start with http:// or https://"
        if '.' not in url:
            return "URL seems invalid (no domain)"
        return None

    def _submit(self) -> None:
        url = self.query_one(Input).value.strip()
        error = self._validate_url(url)
        if error:
            t = Text(error, style="bold #ff6b6b")
            self.query_one("#feed-url-error", Static).update(t)
            self.notify(error, severity="warning", timeout=3)
        else:
            self.dismiss(url)


class PathInputDialog(Screen[str | None]):
    """Modal dialog for entering a file path (import/export)."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, title: str, placeholder: str = "path/to/file") -> None:
        super().__init__()
        self._title = title
        self._placeholder = placeholder

    def compose(self) -> ComposeResult:
        yield Static(self._title, classes="dialog-title")
        yield Input(placeholder=self._placeholder, id="path-input")
        yield Static("", id="path-error", classes="dialog-error")
        yield Button("Submit", id="path-submit-btn", variant="primary")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._submit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self._submit()

    def _submit(self) -> None:
        path = self.query_one(Input).value.strip()
        if path:
            self.dismiss(path)
        else:
            error = Text("Please enter a path", style="bold #ff6b6b")
            self.query_one("#path-error", Static).update(error)
            self.notify("Please enter a path", severity="warning", timeout=3)
