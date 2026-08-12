# Created: 2026-08-12
# Last Edited: 2026-08-12 17:40 CT (America/Chicago)
# Path: aethernews/theme.py
# Purpose: Custom Textual themes — dark navy + teal palette and light variant.

from __future__ import annotations

from textual.theme import Theme

AETHERNEWS_DARK = Theme(
    name="aethernews-dark",
    primary="#00d2d3",
    secondary="#54a0ff",
    accent="#00d2d3",
    warning="#ff9f43",
    error="#ff6b6b",
    success="#4CAF50",
    foreground="#e8e8e8",
    background="#1a1a2e",
    surface="#1a1a2e",
    panel="#2d2d44",
    boost="#3d3d5c",
    dark=True,
    variables={
        "text-muted": "#b0b0c0",
        "border": "#555577",
        "unread": "#00d2d3",
        "starred": "#ffd166",
    },
)

AETHERNEWS_LIGHT = Theme(
    name="aethernews-light",
    primary="#00838f",
    secondary="#54a0ff",
    accent="#00838f",
    warning="#e65100",
    error="#d32f2f",
    success="#2e7d32",
    foreground="#2f3542",
    background="#f8f9fa",
    surface="#f8f9fa",
    panel="#ffffff",
    boost="#f1f2f6",
    dark=False,
    variables={
        "text-muted": "#636e72",
        "border": "#ced6e0",
        "unread": "#00838f",
        "starred": "#f9a825",
    },
)

THEMES = {
    "aethernews-dark": AETHERNEWS_DARK,
    "aethernews-light": AETHERNEWS_LIGHT,
}
