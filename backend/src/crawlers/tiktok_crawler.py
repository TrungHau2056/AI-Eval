"""
TikTok Crawler — crawl TikTok via multiple Apify actors with fallback chain:
    1. clockworks/tiktok-scraper         (primary)
    2. epctex/tiktok-search-scraper      (fallback #1)
    3. automation-lab/tiktok-search-scraper (fallback #2)
    4. paul_44/tiktok-search             (fallback #3 / legacy)
Pipeline:
    keywords → search (with fallback) → flatten → formatted JSON string
Output là 1 chuỗi JSON formatted sẵn sàng cho IntentAgent.
"""
from __future__ import annotations
import logging
import json
from typing import Any
from src.crawlers.base import BaseCrawler, coerce_text

logger = logging.getLogger(__name__)

# Search actor chain (tried in order until one returns usable results):
#   1. clockworks/tiktok-scraper (primary — uses platform credits)
#   2. epctex/tiktok-search-scraper (fallback #1 — may return demo placeholders on free tier)
#   3. automation-lab/tiktok-search-scraper (fallback #2)
#   4. paul_44/tiktok-search (legacy fallback #3)
SEARCH_ACTOR = "clockworks/tiktok-scraper"
FALLBACK_SEARCH_ACTOR_1 = "epctex/tiktok-search-scraper"
FALLBACK_SEARCH_ACTOR_2 = "automation-lab/tiktok-search-scraper"
LEGACY_SEARCH_ACTOR = "paul_44/tiktok-search"


class TiktokCrawler(BaseCrawler):
    """Pipeline crawl TikTok: search (with 3-level fallback)."""

    def __init__(
        self,
        apify_token: str,
        search_limit: int = 20,
    ) -> None:
        super().__init__(apify_token)
        self.search_limit = search_limit

    # ==================================================================
    # Search methods — one per actor (different input schemas)
    # ==================================================================

    async def search_posts(self, query: str) -> list[dict[str, Any]]:
        """Search TikTok — primary actor, then cascade through fallbacks."""
        # ---- 1. Primary: clockworks/tiktok-scraper ----
        try:
            items = await self._run_actor(SEARCH_ACTOR, {
                "searchQueries": [query],
                "resultsPerPage": self.search_limit,
                "maxProfilesPerQuery": self.search_limit,
            })
            filtered = self._flatten_items(items)
            if filtered:
                logger.info("Primary TikTok search '%s' → %d results.", query, len(filtered))
                return items  # return raw items; run() will flatten
        except Exception as exc:
            logger.error("Primary TikTok search failed for '%s': %s", query, exc)

        # ---- 2. Fallback #1: epctex/tiktok-search-scraper ----
        logger.warning(
            "Primary TikTok actor returned 0 rows for '%s' — trying epctex fallback.", query,
        )
        fallback1 = await self._epctex_search(query)
        fallback1_flat = self._flatten_items(fallback1)
        if fallback1_flat:
            logger.info("Epctex fallback '%s' → %d results.", query, len(fallback1_flat))
            return fallback1

        # ---- 3. Fallback #2: automation-lab/tiktok-search-scraper ----
        logger.warning(
            "Epctex fallback returned 0 rows for '%s' — trying automation-lab fallback.", query,
        )
        fallback2 = await self._automation_lab_search(query)
        fallback2_flat = self._flatten_items(fallback2)
        if fallback2_flat:
            logger.info("Automation-lab fallback '%s' → %d results.", query, len(fallback2_flat))
            return fallback2

        # ---- 4. Legacy fallback: paul_44/tiktok-search ----
        logger.warning(
            "Automation-lab fallback returned 0 rows for '%s' — trying paul_44 legacy.", query,
        )
        legacy = await self._paul44_search(query)
        legacy_flat = self._flatten_items(legacy)
        if legacy_flat:
            logger.info("Paul_44 legacy '%s' → %d results.", query, len(legacy_flat))
        else:
            logger.warning("All TikTok search actors returned 0 rows for '%s'.", query)
        return legacy

    async def _epctex_search(self, query: str) -> list[dict[str, Any]]:
        """Fallback #1 via epctex/tiktok-search-scraper."""
        run_input: dict[str, Any] = {
            "searchQueries": [query],
            "maxItems": self.search_limit,
        }
        try:
            return await self._run_actor(FALLBACK_SEARCH_ACTOR_1, run_input)
        except Exception as exc:
            logger.error("Epctex TikTok search failed for '%s': %s", query, exc)
            return []

    async def _automation_lab_search(self, query: str) -> list[dict[str, Any]]:
        """Fallback #2 via automation-lab/tiktok-search-scraper."""
        run_input: dict[str, Any] = {
            "keywords": [query],
            "maxResults": self.search_limit,
        }
        try:
            return await self._run_actor(FALLBACK_SEARCH_ACTOR_2, run_input)
        except Exception as exc:
            logger.error("Automation-lab TikTok search failed for '%s': %s", query, exc)
            return []

    async def _paul44_search(self, query: str) -> list[dict[str, Any]]:
        """Legacy fallback via paul_44/tiktok-search."""
        run_input: dict[str, Any] = {
            "query": query,
            "maxResults": self.search_limit,
        }
        try:
            return await self._run_actor(LEGACY_SEARCH_ACTOR, run_input)
        except Exception as exc:
            logger.error("Paul_44 TikTok search failed for '%s': %s", query, exc)
            return []

    @staticmethod
    def _flatten_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Unwrap grouped actor results; drop demo / empty placeholders."""
        flat: list[dict[str, Any]] = []
        demo_count = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("demo") is True:
                demo_count += 1
                continue
            if item.get("noResults") is True:
                continue

            nested_lists = (
                item.get("videos")
                or item.get("items")
                or item.get("posts")
                or item.get("results")
            )
            if isinstance(nested_lists, list) and nested_lists:
                for v in nested_lists:
                    if isinstance(v, dict) and v.get("demo") is not True and not v.get("noResults"):
                        flat.append(v)
                continue
            flat.append(item)

        if demo_count and not flat:
            logger.warning(
                "TikTok actor returned %d demo placeholder item(s) only — no real video data.",
                demo_count,
            )
        return flat

    @staticmethod
    def _normalize_post(post: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(post, dict):
            return {}
        for key in ("item", "itemStruct", "aweme_info", "aweme"):
            nested = post.get(key)
            if isinstance(nested, dict):
                return {**post, **nested}
        video = post.get("video")
        if isinstance(video, dict):
            return {**post, **video}
        return post

    async def run(self, keywords: list[str]) -> str:
        all_posts: list[dict[str, Any]] = []
        for keyword in keywords:
            logger.info("=" * 60)
            logger.info("Processing TikTok keyword: '%s'", keyword)

            search_results = self._flatten_items(await self.search_posts(keyword))
            if not search_results:
                logger.warning("No TikTok search results for keyword '%s' — skipping.", keyword)
                continue

            all_posts.extend(search_results)

        return self._format_output(all_posts)

    @staticmethod
    def _extract_text(post: dict[str, Any]) -> str:
        p = TiktokCrawler._normalize_post(post)
        for key in ("text", "desc", "description", "title", "caption"):
            text = coerce_text(p.get(key))
            if text:
                return text
        return ""

    @staticmethod
    def _extract_url(post: dict[str, Any]) -> str:
        p = TiktokCrawler._normalize_post(post)
        if isinstance(p.get("webVideoUrl"), str) and p["webVideoUrl"]:
            return p["webVideoUrl"]
        video_id = p.get("id") or p.get("videoId")
        author_meta = p.get("authorMeta") if isinstance(p.get("authorMeta"), dict) else {}
        nickname = p.get("nickname") or author_meta.get("name") or author_meta.get("uniqueId") or ""
        if video_id and nickname:
            return f"https://www.tiktok.com/@{nickname}/video/{video_id}"
        return (
            p.get("url")
            or p.get("videoUrl")
            or "N/A"
        )

    @staticmethod
    def _extract_author(post: dict[str, Any]) -> str:
        p = TiktokCrawler._normalize_post(post)
        author_meta = p.get("authorMeta") if isinstance(p.get("authorMeta"), dict) else {}
        if isinstance(author_meta.get("nickName"), str) and author_meta["nickName"]:
            return author_meta["nickName"].strip()
        if isinstance(author_meta.get("name"), str) and author_meta["name"]:
            return author_meta["name"].strip()
        if isinstance(p.get("nickname"), str) and p["nickname"]:
            return p["nickname"].strip()
        if isinstance(p.get("author"), str) and p["author"]:
            return p["author"].strip()
        return str(p.get("authorName") or "").strip()

    @staticmethod
    def _extract_stats(post: dict[str, Any]) -> dict[str, Any]:
        p = TiktokCrawler._normalize_post(post)
        stats = p.get("stats")
        if isinstance(stats, dict):
            return stats
        return p

    def _format_output(self, posts: list[dict[str, Any]]) -> str:
        if not posts:
            return "[]"

        cleaned_posts = []
        seen_urls: set[str] = set()

        for post in posts:
            p = self._normalize_post(post)
            url = self._extract_url(p)
            text = self._extract_text(p)
            if not text:
                continue
            if url in seen_urls and url != "N/A":
                continue
            seen_urls.add(url)

            author = self._extract_author(p)
            stats = self._extract_stats(p)

            digg_count = stats.get("diggCount") or p.get("diggCount") or p.get("likeCount") or 0
            share_count = stats.get("shareCount") or p.get("shareCount") or 0
            reply_count = stats.get("commentCount") or p.get("commentCount") or 0

            comments: list[str] = []
            if isinstance(p.get("commentsList"), list):
                for c in p["commentsList"]:
                    if isinstance(c, str) and c.strip():
                        comments.append(c.strip())
                    elif isinstance(c, dict):
                        txt = (c.get("text") or c.get("content") or "").strip()
                        if txt:
                            comments.append(txt)

            author_meta = p.get("authorMeta") if isinstance(p.get("authorMeta"), dict) else {}
            cleaned_posts.append({
                "username": author,
                "isVerified": author_meta.get("verified") or p.get("isVerified") or False,
                "captionText": text,
                "takenAtFormatted": p.get("createTimeISO") or str(p.get("createTime", "")),
                "likeCount": digg_count,
                "directReplyCount": reply_count,
                "repostCount": share_count,
                "postUrl": url,
                "comments": comments[:3],
            })

        if posts and not cleaned_posts:
            logger.warning(
                "TikTok formatter dropped %d raw item(s) — no caption text in known fields.",
                len(posts),
            )

        return json.dumps(cleaned_posts, ensure_ascii=False, indent=2)
