"""Persist merged social crawl posts to a JSON file for the FE sheet + /api/discover."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from src.config import BACKEND_DIR

CRAWL_POSTS_PATH = os.path.join(BACKEND_DIR, "data", "crawl_posts.json")


def _ensure_data_dir() -> None:
    os.makedirs(os.path.dirname(CRAWL_POSTS_PATH), exist_ok=True)


def _post_key(post: dict[str, Any]) -> str:
    return f"{post.get('platform', '')}|{post.get('url', '')}"


def load_posts() -> list[dict[str, Any]]:
    if not os.path.isfile(CRAWL_POSTS_PATH):
        return []
    try:
        with open(CRAWL_POSTS_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError, TypeError):
        return []
    if isinstance(data, dict):
        posts = data.get("posts")
        return posts if isinstance(posts, list) else []
    return data if isinstance(data, list) else []


def save_posts(posts: list[dict[str, Any]]) -> None:
    _ensure_data_dir()
    payload = {
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "posts": posts,
    }
    with open(CRAWL_POSTS_PATH, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def clear_posts() -> None:
    if os.path.isfile(CRAWL_POSTS_PATH):
        os.remove(CRAWL_POSTS_PATH)


def prepend_posts(new_posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prepend freshly crawled rows to the top of the sheet; dedupe by platform+url."""
    stamped = []
    now = datetime.now(timezone.utc).isoformat()
    for post in new_posts:
        if not isinstance(post, dict):
            continue
        stamped.append({**post, "crawledAt": post.get("crawledAt") or now})

    existing = load_posts()
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()

    for post in stamped + existing:
        key = _post_key(post)
        if post.get("url"):
            if key in seen:
                continue
            seen.add(key)
        merged.append(post)

    save_posts(merged)
    return merged


def posts_to_raw_content(posts: list[dict[str, Any]]) -> str:
    """Rebuild crawler-style JSON for IntentAgent /api/discover from stored sheet rows."""
    items = []
    for post in posts:
        if not isinstance(post, dict):
            continue
        text = post.get("text") or ""
        if not text:
            continue
        items.append({
            "username": post.get("username") or "",
            "captionText": text,
            "takenAtFormatted": post.get("postingDate") or "",
            "likeCount": post.get("likes") or 0,
            "directReplyCount": post.get("commentsCount") or 0,
            "postUrl": post.get("url") or "",
            "platform": post.get("platform") or "",
            "comments": [],
        })
    return json.dumps(items, ensure_ascii=False, indent=2)
