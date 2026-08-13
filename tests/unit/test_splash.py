# Created: 2026-08-13
# Last Edited: 2026-08-13 15:47 CT (America/Chicago)
# Path: tests/unit/test_splash.py
# Purpose: TUI tests for the startup splash screen.

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from aethernews.app import AetherNews
from aethernews.engine import DataManager
from aethernews.models import Article, FeedResult
from aethernews.screens.splash import SplashScreen


def _seed(path: Path) -> None:
    dm = DataManager(path)
    dm.add_feed("https://example.com/t.xml")
    dm.save_cached_result("https://example.com/t.xml", FeedResult(
        title="T", articles=[Article(title="A", url="u",
                                     published="2026-08-13T08:00:00Z",
                                     article_id="a1")]))


def test_splash_shows_on_launch():
    path = Path(tempfile.mkstemp(suffix=".json")[1])
    _seed(path)
    def run():
        app = AetherNews(data_path=path)
        async def main():
            async with app.run_test() as pilot:
                await pilot.pause()
                assert isinstance(app.screen, SplashScreen)
                # content + hint widgets present
                content = app.screen.query_one("#splash-content")
                hint = app.screen.query_one("#splash-hint")
                assert content is not None
                assert "Press any key" in hint.renderable
        asyncio.run(main())
    run()


def test_any_key_dismisses_splash_to_feed():
    path = Path(tempfile.mkstemp(suffix=".json")[1])
    _seed(path)
    def run():
        app = AetherNews(data_path=path)
        async def main():
            async with app.run_test() as pilot:
                await pilot.pause()
                assert isinstance(app.screen, SplashScreen)
                await pilot.press("space")
                await pilot.pause()
                from aethernews.screens.feed_screen import FeedScreen
                assert isinstance(app.screen, FeedScreen)
        asyncio.run(main())
    run()


def test_splash_auto_dismisses_after_4s():
    path = Path(tempfile.mkstemp(suffix=".json")[1])
    _seed(path)
    def run():
        app = AetherNews(data_path=path)
        async def main():
            async with app.run_test() as pilot:
                await pilot.pause()
                assert isinstance(app.screen, SplashScreen)
                # 4s timer; wait a bit past it
                for _ in range(50):
                    await pilot.pause(0.1)
                from aethernews.screens.feed_screen import FeedScreen
                assert isinstance(app.screen, FeedScreen)
        asyncio.run(main())
    run()
