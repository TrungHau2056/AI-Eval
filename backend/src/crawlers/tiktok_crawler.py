"""
TikTok Crawler — crawl TikTok via epctex/tiktok-search-scraper.
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

# ---------------------------------------------------------------------------
# Actor IDs (Apify Store)
# ---------------------------------------------------------------------------
SEARCH_ACTOR = "epctex/tiktok-search-scraper"

class TiktokCrawler(BaseCrawler):
    """Pipeline crawl TikTok: search."""

    def __init__(
        self,
        apify_token: str,
        search_limit: int = 20,
    ) -> None:
        super().__init__(apify_token)
        self.search_limit = search_limit

    async def search_posts(self, query: str) -> list[dict[str, Any]]:
        """
        Search TikTok lấy list video object (chứa url, view, tim, comment_count).
        """
        run_input: dict[str, Any] = {
            "search": [query],
            "maxItems": self.search_limit,
            "sortType": "RELEVANCE",
            "dateRange": "DEFAULT"
        }
        try:
            items = await self._run_actor(SEARCH_ACTOR, run_input)
        except Exception as exc:
            logger.error("TikTok Search failed for '%s': %s", query, exc)
            return []
        logger.info("TikTok Search '%s' → %d results.", query, len(items))
        return items

    async def run(self, keywords: list[str]) -> str:
        """
        Full pipeline:
            keywords → search → format JSON string
        """
        all_posts: list[dict[str, Any]] = []
        for keyword in keywords:
            logger.info("=" * 60)
            logger.info("Processing TikTok keyword: '%s'", keyword)
            
            # Search TikTok cho keyword gốc
            search_results = await self.search_posts(keyword)
            if not search_results:
                logger.warning("No TikTok search results for keyword '%s' — skipping.", keyword)
                continue
                
            all_posts.extend(search_results)
            
        return self._format_output(all_posts)

    # ==================================================================
    # Format helpers
    # ==================================================================
    @staticmethod
    def _extract_text(post: dict[str, Any]) -> str:
        """Trích text chính (caption) từ TikTok video."""
        return (
            post.get("text")
            or post.get("desc")
            or post.get("description")
            or post.get("title")
            or ""
        ).strip()

    @staticmethod
    def _extract_url(post: dict[str, Any]) -> str:
        """Trích URL từ TikTok video."""
        return (
            post.get("url")
            or post.get("videoUrl")
            or post.get("webVideoUrl")
            or "N/A"
        )

    @staticmethod
    def _extract_author(post: dict[str, Any]) -> str:
        """Trích username tác giả."""
        author_meta = post.get("authorMeta") or post.get("author") or {}
        if isinstance(author_meta, dict):
            author = (
                author_meta.get("name")
                or author_meta.get("nickName")
                or author_meta.get("id")
                or author_meta.get("uniqueId")
                or ""
            )
        else:
            author = str(author_meta)
            
        if not author:
            author = post.get("authorName") or post.get("nickname") or ""
        return str(author).strip()

    def _format_output(self, posts: list[dict[str, Any]]) -> str:
        """
        Format list posts thành JSON string cho IntentAgent.
        """
        import json
        if not posts:
            return "[]"
            
        cleaned_posts = []
        seen_urls: set[str] = set()
        
        for post in posts:
            url = self._extract_url(post)
            text = self._extract_text(post)
            if not text:
                continue
            if url in seen_urls and url != "N/A":
                continue
            seen_urls.add(url)
            
            author = self._extract_author(post)
            
            # Map TikTok stats
            digg_count = post.get("diggCount") or post.get("likes") or post.get("likeCount") or 0
            share_count = post.get("shareCount") or post.get("shares") or 0
            reply_count = post.get("commentCount") or post.get("comments") or 0
            
            # TikTok search usually doesn't return full comments list, only comment counts
            # If the actor does return a few comments preview, we extract them
            comments = []
            if isinstance(post.get("commentsList"), list):
                comments = post.get("commentsList")
            
            cleaned_posts.append({
                "username": author,
                "isVerified": post.get("authorMeta", {}).get("verified") or post.get("isVerified") or False,
                "captionText": text,
                "takenAtFormatted": post.get("createTimeISO") or str(post.get("createTime", "")),
                "likeCount": digg_count,
                "directReplyCount": reply_count,
                "repostCount": share_count,
                "postUrl": url,
                "comments": comments[:3]
            })
            
        return json.dumps(cleaned_posts, ensure_ascii=False, indent=2)
