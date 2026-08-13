# Created: 2026-08-13
# Last Edited: 2026-08-13 15:43 CT (America/Chicago)
# Path: aethernews/splash.py
# Purpose: Startup splash screen renderable — ASCII logo, app stats, and features list.

from __future__ import annotations

from rich.console import Console, ConsoleOptions, RenderResult
from rich.table import Table
from rich.text import Text

from aethernews import __version__

# Theme colors (from aethernews/theme.py dark palette)
BG = "#1a1a2e"
TEAL = "#00d2d3"
BLUE = "#54a0ff"
GREEN = "#4CAF50"
FG = "#e8e8e8"
MUTED = "#b0b0c0"
BORDER = "#555577"
FEATURES_TEAL = "#00d2d3"

AETHER_LOGO = r"""
╔══════════════════════════════╗
║       A E T H E R N E W S    ║
║   Terminal News Reader       ║
╚══════════════════════════════╝
"""

FEATURES = [
    "Subscribe to any RSS/Atom news feed",
    "Category-grouped overview with recency markers",
    "Read articles in a clean, scrollable reader",
    "Star / unread tracking per article",
    "48-hour hot-band coloring on fresh articles",
    "OPML import / export",
    "Dark / light theme toggle",
    "Recency-first article sorting",
    "Async feed refresh \u2014 instant cache",
]


def _empty() -> Text:
    return Text("  ", style=f"on {BG}")


def _val(label: str, value: str, accent: str = GREEN) -> Text:
    return Text.assemble(
        Text(f"  {label}: ", style=f"{BLUE} on {BG}"),
        Text(value, style=f"{accent} on {BG}"),
    )


class SplashRenderable:
    """Rich renderable for the startup splash: logo left, stats right."""

    def __init__(self, n_feeds: int, n_unread: int, n_categories: int) -> None:
        self._n_feeds = n_feeds
        self._n_unread = n_unread
        self._n_categories = n_categories

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        logo_lines = AETHER_LOGO.strip("\n").split("\n")
        logo_width = max(len(l) for l in logo_lines) if logo_lines else 0

        right_lines: list[Text] = [
            Text(f"  AetherNews v{__version__}", style=f"bold {TEAL} on {BG}"),
            _empty(),
            Text("  Terminal News Reader", style=f"italic {MUTED} on {BG}"),
            _empty(),
            _val("Feeds", str(self._n_feeds)),
            _val("Unread", str(self._n_unread)),
            _val("Categories", str(self._n_categories)),
            _empty(),
            Text("  Features:", style=f"bold {FEATURES_TEAL} on {BG}"),
        ]

        for f in FEATURES:
            right_lines.append(Text(f"  \u2022 {f}", style=f"{FG} on {BG}"))

        right_lines.append(_empty())
        right_lines.append(
            Text("  Python 3.9+  \u00b7  Textual  \u00b7  feedparser  \u00b7  GPLv3",
                 style=f"dim {MUTED} on {BG}")
        )

        rh = len(right_lines)
        logo_h = len(logo_lines)
        pad_top = (rh - logo_h) // 2
        pad_bot = rh - logo_h - pad_top
        left_padded = (
            [Text(" " * logo_width, style=f"on {BG}")] * pad_top
            + [Text(l, style=f"{TEAL} on {BG}") for l in logo_lines]
            + [Text(" " * logo_width, style=f"on {BG}")] * pad_bot
        )

        table = Table.grid(expand=False, padding=0)
        table.add_column("left", justify="center", width=logo_width + 2)
        table.add_column("sep", justify="center", width=3)
        table.add_column("right", justify="left", width=56)

        for i in range(rh):
            left_cell = (
                left_padded[i]
                if i < len(left_padded)
                else Text(" " * logo_width, style=f"on {BG}")
            )
            sep = Text(" \u2502 ", style=f"bold {BORDER} on {BG}")
            table.add_row(left_cell, sep, right_lines[i])

        yield table
