# AetherNews

Terminal RSS News Reader — subscribe to feeds, read articles in your terminal.

A sibling project to [AetherPod](https://github.com/AetherSolDev/AetherPod) (the
podcast manager). AetherNews reuses AetherPod's proven patterns — feedparser,
aiohttp, Textual, TTL-cached feeds, OPML — but is a **completely separate
application** with its own schema and state file. No shared code, no merging.

## Features

- **Subscribe & browse** — RSS/Atom feeds, unread badges, read/unread toggling
- **Full-article reader** — HTML converted to plain text, scrollable, `o` to
  open the original article in your browser
- **Starred articles** — `*` to save for later
- **Categories** — tag a feed, filter by category with `c`
- **TTL cache** — feeds checked within 6h are skipped on refresh; `304 Not
  Modified` bumps the freshness window
- **Retention** — the newest ~200 articles within 30 days per feed (news is
  high-volume and short-lived; no full-history merging)
- **OPML** import/export, sort, filter, search, dark/light theme

## Install

```bash
pip install -e .
```

Or run without installing:

```bash
python aethernews.py tui
```

## Usage

```bash
aethernews tui            # launch the TUI
aethernews add https://.../feed.xml   # subscribe
aethernews list           # list feeds
aethernews refresh        # fetch all feeds (respects TTL)
aethernews import subs.opml
aethernews export subs.opml
aethernews reset          # clear all state
```

## Keybindings

### Feed screen
`a` add feed · `i` import OPML · `e` export OPML · `u` refresh · `s` sort ·
`f` filter · `c` category filter · `r` remove · Enter browse · `?` help · `q` quit

### Article screen
`Enter` read · `n` next unread · `Space`/`m` toggle read · `*` star · `s` sort ·
`u` refresh · `t` theme · `?` help · `q` quit

### Reader screen
`j`/`k` scroll · `o` open in browser · `s` star · `n` next unread · `q` close

## State

`state.json` lives in the platformdirs user-state dir (`~/.local/state/aethernews/`),
script-relative when a `data/` directory exists next to the code. Logs in
`~/.local/state/aethernews/log/aethernews.log`.

## License

GPLv3
