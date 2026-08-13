# Created: 2026-08-12
# Last Edited: 2026-08-13 12:42 CT (America/Chicago)
# Path: aethernews/screens/dialogs.py
# Purpose: Input dialogs — AddFeedDialog, PathInputDialog, CategoryDialog.

from __future__ import annotations

import re

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Button, Input, Select, Static


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


class CategoryDialog(Screen[str | None]):
    """Modal dialog for assigning a category to the selected feed.

    The dialog returns the chosen category name, or ``""`` to clear the
    feed back to "Uncategorized", or ``None`` when cancelled.  A category
    name typed in the input is used as-is, so new categories are created
    simply by typing their name.
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(
        self,
        feed_title: str,
        current_category: str,
        existing: list[str],
    ) -> None:
        super().__init__()
        self._feed_title = feed_title
        self._current = current_category
        self._existing = existing

    def compose(self) -> ComposeResult:
        yield Static("", id="dialog-box")
        yield Static(f"Category for \u201c{self._feed_title}\u201d",
                     classes="dialog-title")
        yield Static("New or existing category:", id="cat-prompt",
                     classes="dialog-error")
        yield Input(
            placeholder="type a new category name\u2026",
            id="cat-input",
            value=self._current,
        )
        yield Static("or pick an existing one:", id="cat-pick-prompt",
                     classes="dialog-error")
        options: list[tuple[str, str]] = [
            ("\u2014 Uncategorized \u2014", ""),
        ]
        for name in self._existing:
            options.append((name, name))
        yield Select(options, prompt="Choose category\u2026",
                     id="cat-select", value=self._current)
        yield Static("", id="cat-error", classes="dialog-error")
        yield Button("Apply", id="cat-apply-btn", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#cat-input", Input).focus()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "cat-input":
            # Clear the picker error when typing a fresh name.
            self.query_one("#cat-error", Static).update("")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "cat-select" and event.value is not Select.BLANK:
            self.query_one("#cat-input", Input).value = event.value

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "cat-input":
            self._submit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self._submit()

    def _submit(self) -> None:
        name = self.query_one("#cat-input", Input).value.strip()
        self.dismiss(name)
