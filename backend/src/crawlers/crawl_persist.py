"""Shared helpers for crawl endpoints: parse, persist, sync pipeline state."""
from __future__ import annotations

import json
from typing import Any

from src.api.deps import get_state
from src.crawlers.crawl_store import posts_to_raw_content, prepend_posts


def parse_crawler_posts(raw_content: str, platform: str) -> list[dict[str, Any]]:
    try:
        items = json.loads(raw_content)
    except (ValueError, TypeError):
        return []
    if not isinstance(items, list):
        return []

    posts: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        text = item.get("captionText") or item.get("text") or ""
        if not text:
            continue
        posts.append({
            "platform": platform,
            "url": item.get("postUrl") or item.get("url") or "",
            "postingDate": item.get("takenAtFormatted") or "",
            "text": text,
            "likes": item.get("likeCount") or 0,
            "commentsCount": item.get("directReplyCount") or 0,
            "username": item.get("username") or "",
        })
    return posts


def persist_crawl_posts(platform: str, raw_content: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Parse this crawl, prepend to JSON store, sync merged raw content to pipeline state."""
    new_posts = parse_crawler_posts(raw_content, platform)
    all_posts = prepend_posts(new_posts)
    get_state().raw_social_content = posts_to_raw_content(all_posts)
    return new_posts, all_posts
