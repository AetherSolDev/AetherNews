# Created: 2026-08-12
# Last Edited: 2026-08-12 17:40 CT (America/Chicago)
# Path: aethernews/cli.py
# Purpose: CLI entry point logic — argparse, logging setup, headless commands, TUI launch.

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from platformdirs import user_state_dir

from aethernews import __version__
from aethernews.engine import DataManager
from aethernews.rss import fetch_feed

_SCRIPT_DIR = Path(__file__).resolve().parent.parent

_LOG_DIR = Path(user_state_dir("aethernews", ensure_exists=True)) / "log"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

_LOG_LEVEL = os.environ.get("AETHERNEWS_LOG_LEVEL", "INFO").upper()

_LOG_FILE = _LOG_DIR / "aethernews.log"

_log_level = getattr(logging, _LOG_LEVEL, logging.INFO)

_log_stderr = logging.StreamHandler(stream=sys.stderr)
_log_stderr.setLevel(logging.WARNING)

logging.basicConfig(
    level=_log_level,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
    handlers=[
        _log_stderr,
        logging.FileHandler(str(_LOG_FILE), encoding="utf-8", delay=False),
    ],
)
logger = logging.getLogger("aethernews")
logger.info("Logging to %s", _LOG_FILE)


def cmd_list(data: DataManager) -> None:
    for url in data.get_feeds():
        result = fetch_feed(url)
        if result.error:
            print(f"  \u2717 {url} \u2014 {result.error}")
        else:
            unread = sum(1 for a in result.articles if data.is_unread(a.article_id or ""))
            print(f"  {result.title} ({len(result.articles)} articles, {unread} unread)")
            print(f"    {url}")


def cmd_add(data: DataManager, url: str) -> None:
    if data.add_feed(url):
        print(f"Added feed: {url}")
    else:
        print(f"Feed already subscribed: {url}")


def cmd_refresh(data: DataManager) -> None:
    for url in data.get_feeds():
        if data.is_cache_fresh(url):
            checked = data.last_checked(url)
            print(f"\u25b8 {url} (fresh \u2014 last checked {checked})")
            continue
        result = fetch_feed(url)
        if result.error:
            print(f"\u2717 {url}: {result.error}")
            continue
        data.save_cached_result(url, result)
        if result.etag or result.last_modified:
            data.save_feed_headers(url, result.etag, result.last_modified)
        unread = sum(1 for a in result.articles if data.is_unread(a.article_id or ""))
        print(f"\n=== {result.title} ===")
        for a in result.articles[:5]:
            marker = "\u2713" if not data.is_unread(a.article_id or "") else " "
            print(f"  [{marker}] {a.title}")
        print(f"  ({len(result.articles)} articles, {unread} unread)")


def cmd_import_opml(data: DataManager, path: str) -> None:
    count = data.opml_import(path)
    print(f"Imported {count} feed(s) from {path}")


def cmd_export_opml(data: DataManager, path: str) -> None:
    count = data.opml_export(path)
    print(f"Exported {count} feed(s) to {path}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="aethernews", description="Terminal RSS news reader")
    parser.add_argument("--data", default="",
                        help="Path to state file (default: XDG state dir)")
    parser.add_argument("-v", "--version", action="store_true", help="Show version and exit")
    parser.add_argument("--verbose", action="store_true",
                        help="Verbose output (set log level to DEBUG)")
    parser.add_argument("--debug", action="store_true",
                        help="Alias for --verbose")

    sub = parser.add_subparsers(dest="command")
    sub.add_parser("list", help="List subscribed feeds")
    sub.add_parser("tui", help="Launch the TUI (default)")
    add_p = sub.add_parser("add", help="Subscribe to a feed URL")
    add_p.add_argument("url")
    sub.add_parser("refresh", help="Fetch all feeds and show new articles")
    sub.add_parser("reset", help="Clear all state")
    import_p = sub.add_parser("import", help="Import feeds from OPML file")
    import_p.add_argument("path", help="Path to OPML file")
    export_p = sub.add_parser("export", help="Export feeds to OPML file")
    export_p.add_argument("path", help="Output path for OPML file")

    args = parser.parse_args()

    if args.verbose or args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")

    if args.version:
        print(f"AetherNews {__version__}")
        return

    data_path = None
    if args.data:
        p = Path(args.data)
        if not p.is_absolute():
            p = (_SCRIPT_DIR / args.data).resolve()
        data_path = p
    data = DataManager(data_path)

    if args.command == "list":
        cmd_list(data)
    elif args.command == "add":
        cmd_add(data, args.url)
    elif args.command == "refresh":
        cmd_refresh(data)
    elif args.command == "import":
        cmd_import_opml(data, args.path)
    elif args.command == "export":
        cmd_export_opml(data, args.path)
    elif args.command == "reset":
        print(f"Reset: removing {data._path}")
        data._path.unlink(missing_ok=True)
        data.load()
    else:
        from aethernews.app import AetherNews

        app = AetherNews(data_path=data_path)
        app.run()


if __name__ == "__main__":
    main()
