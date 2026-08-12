# Created: 2026-08-12
# Last Edited: 2026-08-12 17:40 CT (America/Chicago)
# Path: aethernews/models.py
# Purpose: Shared dataclasses — Article, FeedResult.

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Article:
    """Represents a single news article from an RSS/Atom feed."""

    title: str
    url: str
    published: str | None = None
    summary: str | None = None
    content: str | None = None
    author: str | None = None
    article_id: str | None = None


@dataclass
class FeedResult:
    """Result of fetching and parsing an RSS feed."""

    title: str
    articles: list[Article]
    error: str | None = None
    not_modified: bool = False
    etag: str = ""
    last_modified: str = ""
