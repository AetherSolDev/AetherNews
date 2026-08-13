# Created: 2026-08-12
# Last Edited: 2026-08-13 14:05 CT (America/Chicago)
# Path: aethernews/screens/detail_help.py
# Purpose: Modal overlays — ReaderScreen (full article) and HelpScreen.

from __future__ import annotations

import html
import re

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Footer, Static

from aethernews import __version__
from aethernews.models import Article
from aethernews.screens.helpers import format_date


def html_to_text(raw: str | None) -> str:
    """Convert a snippet of HTML into plain text suitable for the reader.

    Strips tags, unescapes entities, collapses whitespace, and preserves
    paragraph/line breaks.  Used for the full-article reader pane.
    """
    if not raw:
        return ""
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", raw, flags=re.DOTALL | re.IGNORECASE)
    # Split into paragraphs on block boundaries, then <br> = hard newline
    # within a paragraph (no extra blank line).
    text = re.sub(r"</(p|div|li|h[1-6]|tr)>", "\x00P", text, flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\x00B", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)

    paragraphs: list[str] = []
    for chunk in text.split("\x00P"):
        lines = [re.sub(r"[ \t]+", " ", ln).strip()
                 for ln in chunk.split("\x00B")]
        lines = [ln for ln in lines if ln]
        if lines:
            paragraphs.append("\n".join(lines))
    return "\n\n".join(paragraphs)


class ReaderScreen(Screen[None]):
    """Full-screen article reader — HTML converted to a scrollable text pane.

    Marks the article as read when the screen is pushed, and offers
    ``o`` to open the article URL in the default browser.
    """

    BINDINGS = [
        Binding("escape,enter,q", "dismiss", "Close"),
        Binding("o", "open_link", "Open in browser", key_display="o"),
        Binding("s", "toggle_star", "Star"),
        Binding("j,down", "scroll_down", "Down", key_display="j/↓"),
        Binding("k,up", "scroll_up", "Up", key_display="k/↑"),
        Binding("n", "next_unread", "Next unread", key_display="n"),
        Binding("question_mark", "show_help", "Help", key_display="?"),
    ]

    def __init__(self, article: Article, data_manager) -> None:
        super().__init__()
        self._article = article
        self._data = data_manager

    def compose(self) -> ComposeResult:
        yield Static("", id="reader-header", classes="dialog-title")
        with VerticalScroll(id="reader-body"):
            yield Static("", id="reader-body-content")
        yield Footer()

    def on_mount(self) -> None:
        art = self._article
        # Matches AetherPod: viewing an article does NOT mark it read.
        # Only an explicit space/m toggle does.
        self._update_star_header()

        body = Text()
        meta = []
        if art.published:
            meta.append(f"\U0001f4c5 {format_date(art.published)}")
        if art.author:
            meta.append(f"\U0001f464 {art.author}")
        if art.url:
            meta.append(art.url)
        if meta:
            body.append("  " + "   ·   ".join(meta), style="dim")
            body.append("\n\n", style="")

        article_text = html_to_text(art.content or art.summary or "")
        if article_text:
            body.append(article_text, style="")
        else:
            body.append("  (No content)", style="dim")
        self.query_one("#reader-body-content", Static).update(body)

    def action_toggle_star(self) -> None:
        now_starred = self._data.toggle_starred(self._article.article_id or "")
        self.notify("Starred ★" if now_starred else "Unstarred", severity="information", timeout=1)
        self._update_star_header()

    def _update_star_header(self) -> None:
        art = self._article
        header = Text()
        if self._data.is_starred(art.article_id or ""):
            header.append("★ ", style="bold yellow")
        else:
            header.append("  ", style="")
        header.append(art.title or "(no title)", style="bold")
        self.query_one("#reader-header", Static).update(header)

    def action_open_link(self) -> None:
        import webbrowser

        url = self._article.url
        if not url:
            self.notify("No article link", severity="warning", timeout=2)
            return
        webbrowser.open(url)
        self.notify("Opened in browser", severity="information", timeout=2)

    def action_scroll_down(self) -> None:
        body = self.query_one("#reader-body", VerticalScroll)
        if body.scroll_target_y >= body.max_scroll_y:
            # At the bottom — jump to the next unread article.
            self.action_next_unread()
            return
        body.scroll_down()

    def action_scroll_up(self) -> None:
        self.query_one("#reader-body", VerticalScroll).scroll_up()

    def action_next_unread(self) -> None:
        # Post to the ArticleScreen below so it can jump to the next unread.
        from aethernews.screens.article_screen import ArticleScreen

        target = next(
            (s for s in self.app.screen_stack if isinstance(s, ArticleScreen)),
            None,
        )
        self.dismiss()
        if target is not None:
            target.post_message(
                NextUnreadRequested(self._article.article_id or "")
            )

    def action_show_help(self) -> None:
        self.app.push_screen(HelpScreen(screen_name="Reader"))

    def action_dismiss(self) -> None:
        self.app.pop_screen()


class NextUnreadRequested(Message):
    """Posted when the reader asks to jump to the next unread article."""

    def __init__(self, current_id: str) -> None:
        super().__init__()
        self.current_id = current_id


class HelpScreen(Screen[None]):
    BINDINGS = [
        Binding("escape,space,enter,q,question_mark", "dismiss", "Close", key_display="Esc"),
    ]

    _BINDINGS_BY_SCREEN = {
        "Feed": [
            ("a", "Add a feed URL"),
            ("i", "Import OPML file"),
            ("e", "Export OPML file"),
            ("u", "Refresh all feeds"),
            ("s", "Sort: newest-first \u2194 subscribe order"),
            ("f", "Filter feeds by name"),
            ("c", "Categorize the selected feed"),
            ("Space", "Collapse / expand a category"),
            ("\u2192 / \u2190", "Expand / collapse a category"),
            ("\u2191 / \u2193", "Move between rows"),
            ("Enter", "Feed: browse articles \u00b7 Category: toggle"),
            ("\u25cf", "Recently updated (last 24h)"),
            ("q", "Quit AetherNews"),
            ("?", "Show this help"),
        ],
        "Article": [
            ("Esc", "Go back"),
            ("Enter", "Open article in reader"),
            ("n", "Jump to next unread article"),
            ("Space / m", "Toggle read / unread"),
            ("M", "Mark all articles unread"),
            ("*", "Toggle starred"),
            ("u", "Refresh this feed"),
            ("s", "Sort: newest \u2194 unread-first \u2194 A\u2192Z"),
            ("\u2191 / \u2193", "Move selection (arrow keys)"),
            ("t", "Toggle dark/light theme"),
            ("q", "Quit AetherNews"),
            ("?", "Show this help"),
        ],
        "Reader": [
            ("Esc / q", "Close reader"),
            ("j / k / \u2191 / \u2193", "Scroll down / up"),
            ("o", "Open article URL in browser"),
            ("s", "Toggle starred"),
            ("n", "Next unread article"),
            ("?", "Show this help"),
        ],
    }

    def __init__(self, screen_name: str = "Feed") -> None:
        super().__init__()
        self._screen_name = screen_name

    def compose(self) -> ComposeResult:
        yield Static("", id="help-header", classes="dialog-title")
        yield Static("", id="help-content")
        yield Static("Press Esc or ? to close", id="help-footer", classes="status")
        yield Static("", id="help-stack", classes="status")

    def on_mount(self) -> None:
        header = Text()
        header.append("\U0001f4d6 ", style="bold cyan")
        header.append(f"{self._screen_name} Screen Keybindings", style="bold")
        self.query_one("#help-header", Static).update(header)

        bindings = self._BINDINGS_BY_SCREEN.get(self._screen_name, [])
        content = Text()
        for key, desc in bindings:
            content.append(f"  {key:<20}", style="bold cyan")
            content.append(f"  {desc}\n", style="")

        tips = [
            ("t", "toggle dark/light theme"),
        ]
        for key, desc in tips:
            content.append(f"  {key:<20}", style="bold cyan")
            content.append(f"  {desc}\n", style="dim")
        self.query_one("#help-content", Static).update(content)

        stack = Text(
            f"AetherNews v{__version__}  \u2502  Python 3.9+  \u2502  Textual  \u2502  GPLv3",
            style="dim",
        )
        self.query_one("#help-stack", Static).update(stack)

    def action_dismiss(self) -> None:
        self.app.pop_screen()
