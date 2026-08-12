# Created: 2026-08-12
# Last Edited: 2026-08-12 17:57 CT (America/Chicago)
# Path: docs/USER_GUIDE.md
# Purpose: User-facing handbook for AetherNews.

# AetherNews User Guide

## Table of Contents

1. [Getting Started](#getting-started)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Features](#features)
5. [Keybindings](#keybindings)
6. [Configuration](#configuration)
7. [State & Data](#state--data)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)
10. [Support](#support)

---

## Getting Started

AetherNews is a terminal RSS news reader. Subscribe to RSS/Atom feeds, browse
articles with unread badges, read full articles (HTML converted to plain text),
star items for later, organize feeds into categories, and import/export OPML —
all from the terminal. A sibling project to AetherPod (the podcast manager);
both apps are independent with their own state.

## Installation

### System Requirements

- OS: Linux, macOS, Windows (any terminal with ANSI/truecolor support)
- Python: 3.9+
- Dependencies: `feedparser`, `textual`, `aiohttp`, `platformdirs`

### Setup

```bash
git clone https://github.com/AetherSolDev/AetherNews.git
cd AetherNews
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Or install as a package:

```bash
pip install -e .
```

## Quick Start

```bash
aethernews tui                                  # launch the TUI
aethernews add https://example.com/feed.xml     # subscribe to a feed
aethernews refresh                              # fetch new articles
aethernews list                                 # list feeds
```

In the TUI: press `Enter` on a feed to browse articles, `Enter` on an article
to read it, `Space` to toggle read/unread, `q` to quit.

## Features

### Feed List

- Unread badge per feed (`(N, M unread)`), zebra striping, sort (`s`), filter (`f`)
- Category filter (`c`) cycles feeds tagged in a category
- `a` add feed, `i`/`e` import/export OPML, `u` refresh, `r` remove

### Article List

- Bold title = unread; `★` status = starred
- `Enter` opens the article in the reader, `n` jumps to next unread
- `Space`/`m` toggles read/unread, `*` toggles starred, `s` cycles sort
  (unread-first → newest → A–Z)

### Reader

- Full article rendered from HTML (strip tags/scripts, preserve paragraphs)
- `j`/`k` scroll, `o` opens the original URL in your browser, `s` star
- Opening a reader marks the article read

## Keybindings

### Feed screen
`a` add feed · `i` import OPML · `e` export OPML · `u` refresh · `s` sort ·
`f` filter · `c` category filter · `r` remove · Enter browse · `?` help · `q` quit

### Article screen
`Enter` read · `n` next unread · `Space`/`m` toggle read · `*` star · `s` sort ·
`u` refresh · `t` theme · `?` help · `q` quit

### Reader screen
`j`/`k` scroll · `o` open in browser · `s` star · `n` next unread · `q` close

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `AETHERNEWS_LOG_LEVEL` | `INFO` | Log verbosity (`DEBUG` for verbose) |
| `--data <path>` | XDG state dir | Override the `state.json` location |
| `cache_ttl_hours` (state.json) | `6` | Hours a feed cache is considered fresh |

## State & Data

- State file: `~/.local/state/aethernews/state.json`
- Log file: `~/.local/state/aethernews/log/aethernews.log`
- Retention: the newest ~200 articles within 30 days per feed are cached.
  Older/pruned articles drop their unread markers automatically.
- OPML export: `aethernews export subs.opml`

## Troubleshooting

### Common Issue 1 — "No audio engine" / nothing happens

AetherNews is a text reader, not a player — no audio engine needed. If the TUI
won't launch, run `aethernews --verbose tui` and check
`~/.local/state/aethernews/log/aethernews.log`.

### Common Issue 2 — TUI shows garbage / reflows

Ensure your terminal supports truecolor and is wide enough (Textual needs ~80
columns). Resize or use a larger font.

### Common Issue 3 — Articles not marked unread

Unread marking happens on refresh (`save_cached_result`). Articles are unread
when first fetched; opening the reader or pressing `Space` marks them read.

## FAQ

- **Is this a web app?** No — a terminal TUI. A follow-me sync layer (read-only
  web view over `state.json`) is a deferred idea.
- **Does it work on Android/Termux?** All deps are pure Python, so it should
  run; the soft keyboard is the main friction. See PLAN.md (Termux spike).
- **Why JSON not a database?** Single-user app, simple schema, mirrors AetherPod.

## Support

- GitHub Issues: `https://github.com/AetherSolDev/AetherNews/issues`
- Documentation: `docs/`
