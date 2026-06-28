"""
TikTok Crawler — crawl TikTok via clockworks/tiktok-scraper.
Pipeline:
    1. TikTok Search → tìm video TikTok theo keyword, trả về danh sách video có metadata
Output là 1 chuỗi JSON formatted sẵn sàng cho IntentAgent.
"""
from __future__ import annotations
import logging
import json
from typing import Any
from src.crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

# clockworks uses platform credits; epctex returns {"demo": true} placeholders on free tier
SEARCH_ACTOR = "clockworks/tiktok-scraper"


class TiktokCrawler(BaseCrawler):
    """Pipeline crawl TikTok: search."""

    def __init__(
        self,
        apify_token: str,
        search_limit: int = 20,
        max_posts: int = 2,
    ) -> None:
        super().__init__(apify_token)
        self.search_limit = search_limit
        self.max_posts = max_posts

    async def search_posts(self, query: str) -> list[dict[str, Any]]:
        # Fetch đúng max_posts/keyword (không over-fetch) — cap tổng vẫn ở _format_output.
        run_input: dict[str, Any] = {
            "searchQueries": [query],
            "resultsPerPage": self.max_posts,
            "maxProfilesPerQuery": self.max_posts,
        }
        try:
            items = await self._run_actor(SEARCH_ACTOR, run_input)
        except Exception as exc:
            logger.error("TikTok Search failed for '%s': %s", query, exc)
            return []
        logger.info("TikTok Search '%s' → %d results.", query, len(items))
        return items

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
            # Đủ post HỢP LỆ (sau dedup + lọc) → dừng; chưa đủ thì sang keyword kế bù.
            if len(self._clean_posts(all_posts)) >= self.max_posts:
                break
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
        return (
            p.get("text")
            or p.get("desc")
            or p.get("description")
            or p.get("title")
            or p.get("caption")
            or ""
        ).strip()

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

    def _clean_posts(self, posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Dedup theo URL + bỏ post không text + map field. KHÔNG slice/serialize."""
        if not posts:
            return []

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

        return cleaned_posts

    def _format_output(self, posts: list[dict[str, Any]]) -> str:
        # Cap tổng số post mỗi nền tảng (sau dedup + lọc post-không-text).
        cleaned = self._clean_posts(posts)[: self.max_posts]
        return json.dumps(cleaned, ensure_ascii=False, indent=2)
