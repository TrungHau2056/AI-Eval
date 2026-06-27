"""
ThreadsCrawler — crawl Threads qua Google Autocomplete và Apify Threads Scraper.
Pipeline:
    1. Google Autocomplete  →  mở rộng keywords thành nhiều search queries
    2. Threads Search      →  tìm bài viết Threads theo từng query
    3. Threads Posts       →  scrape chi tiết bài viết và replies từ URLs
Output là 1 string formatted sẵn sàng cho IntentAgent.
"""
from __future__ import annotations
import logging
from typing import Any
from src.crawlers.base import BaseCrawler, coerce_text

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Actor IDs (Apify Store)
# ---------------------------------------------------------------------------
AUTOCOMPLETE_ACTOR = "dainins/google-autocomplete-scraper"
SEARCH_SCRAPER= "igview-owner/threads-search-scraper"
POSTS_ACTOR= "logical_scrapers/threads-post-scraper"

class ThreadsCrawler(BaseCrawler):
    """Pipeline crawl Threads: autocomplete → search → scrape."""

    def __init__(
        self,
        apify_token: str,
        autocomplete_limit: int = 5,
        search_limit: int = 20,
        posts_limit: int = 20,
    ) -> None:
        super().__init__(apify_token)
        self.autocomplete_limit = autocomplete_limit
        self.search_limit = search_limit
        self.posts_limit = posts_limit

    # ==================================================================
    # Step 1 — Google Autocomplete
    # ==================================================================
    async def get_autocomplete(
        self,
        keyword: str,
        limit: int | None = None,
    ) -> list[str]:
        """
        Gọi Google Autocomplete Scraper để mở rộng 1 keyword thành nhiều search queries.
        """
        limit = limit or self.autocomplete_limit
        run_input: dict[str, Any] = {
            "queries": [keyword],
            "maxResults": limit,
            "languageCode": "vi",
            "countryCode": "vn",
        }
        try:
            items = await self._run_actor(AUTOCOMPLETE_ACTOR, run_input)
        except Exception as exc:
            logger.error("Autocomplete failed for '%s': %s", keyword, exc)
            return [keyword]          # fallback: dùng chính keyword gốc

        suggestions: list[str] = []
        for item in items:
            results = (
                item.get("results")
                or item.get("suggestions")
                or item.get("autocomplete")
                or []
            )
            if isinstance(results, list):
                for r in results:
                    text = r if isinstance(r, str) else r.get("value", r.get("text", ""))
                    if text and text not in suggestions:
                        suggestions.append(text)
        if not suggestions:
            suggestions = [keyword]    # fallback
        logger.info("Autocomplete '%s' → %d queries: %s", keyword, len(suggestions), suggestions[:5])
        return suggestions[:limit]

    # ==================================================================
    # Step 2 — Threads Search
    # ==================================================================
    async def search_posts(
        self,
        query: str,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Search Threads posts via igview-owner/threads-search-scraper."""
        limit = limit or self.search_limit
        run_input: dict[str, Any] = {
            "searchQuery": query,
            "maxItems": limit,
        }
        try:
            items = await self._run_actor(SEARCH_SCRAPER, run_input)
        except Exception as exc:
            logger.error("Threads Search failed for '%s': %s", query, exc)
            return []
        filtered = self._filter_search_items(items)
        logger.info("Threads Search '%s' → %d results.", query, len(filtered))
        return filtered

    @staticmethod
    def _filter_search_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        valid: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict) or item.get("error"):
                continue
            p = item.get("thread") or item
            url = (
                p.get("url")
                or p.get("postUrl")
                or p.get("link")
                or p.get("permalink")
                or ""
            )
            if url:
                valid.append(item)
        return valid

    # ==================================================================
    # Step 3 — Threads Deep Scrape (scrape by URLs)
    # ==================================================================
    async def scrape_posts(
        self,
        urls: list[str],
    ) -> list[dict[str, Any]]:
        """
        Scrape nội dung chi tiết bài viết Threads từ danh sách URLs.
        """
        if not urls:
            return []
        start_urls = [{"url": u} for u in urls]
        run_input: dict[str, Any] = {
            "startUrls": start_urls,
            "resultsLimit": self.posts_limit,
        }
        try:
            items = await self._run_actor(POSTS_ACTOR, run_input)
        except Exception as exc:
            logger.error("Scrape Threads posts failed: %s", exc)
            return []
        logger.info("Scraped %d Threads posts from %d URLs.", len(items), len(urls))
        return items

    # ==================================================================
    # Orchestrator — chạy toàn bộ pipeline
    # ==================================================================
    async def run(self, keywords: list[str]) -> str:
        """
        Full pipeline:
            keywords → autocomplete → search → scrape → formatted string
        """
        all_posts: list[dict[str, Any]] = []
        for keyword in keywords:
            logger.info("=" * 60)
            logger.info("Processing Threads keyword: '%s'", keyword)
            
            # ---- Step 1: Mở rộng keyword ----
            # ĐÃ TẮT: Tạm thời tắt Autocomplete để tiết kiệm tối đa chi phí $5 Apify
            # queries = await self.get_autocomplete(keyword)
            queries = [keyword]
            
            # ---- Step 2: Search Threads cho mỗi query ----
            search_results: list[dict[str, Any]] = []
            for query in queries:
                results = await self.search_posts(query)
                search_results.extend(results)
            if not search_results:
                logger.warning("No Threads search results for keyword '%s' — skipping.", keyword)
                continue

            posts_with_text = [item for item in search_results if self._extract_text(item)]
            if posts_with_text:
                all_posts.extend(posts_with_text)
                continue

            urls: list[str] = []
            for item in search_results:
                p = item.get("thread") or item
                url = (
                    p.get("url")
                    or p.get("postUrl")
                    or p.get("link")
                    or p.get("permalink")
                    or ""
                )
                if url and url.startswith("http") and url not in urls:
                    urls.append(url)

            urls = urls[: self.posts_limit]

            if urls:
                scraped = self._filter_search_items(await self.scrape_posts(urls))
                if scraped:
                    all_posts.extend(scraped)
                    continue

            logger.info("Falling back to Threads search results for keyword '%s'.", keyword)
            all_posts.extend(search_results)

        # ---- Format output (giới hạn đúng posts_limit bài) ----
        return self._format_output(all_posts, limit=self.posts_limit)

    # ==================================================================
    # Format helpers
    # ==================================================================
    @staticmethod
    def _extract_text(post: dict[str, Any]) -> str:
        """Trích text chính từ Threads post."""
        p = post.get("thread") or post
        for key in ("text", "caption", "captionText", "message", "content", "body"):
            text = coerce_text(p.get(key))
            if text:
                return text
        return ""

    @staticmethod
    def _extract_url(post: dict[str, Any]) -> str:
        """Trích URL từ Threads post."""
        p = post.get("thread") or post
        return (
            p.get("url")
            or p.get("postUrl")
            or p.get("link")
            or p.get("permalink")
            or "N/A"
        )

    @staticmethod
    def _extract_comments(post: dict[str, Any]) -> list[str]:
        """Trích danh sách comment/reply từ Threads post."""
        replies_raw = (
            post.get("replies")
            or post.get("comments")
            or post.get("topComments")
            or []
        )
        comments: list[str] = []
        if isinstance(replies_raw, list):
            for c in replies_raw:
                if isinstance(c, str):
                    txt = c.strip()
                elif isinstance(c, dict):
                    txt = coerce_text(
                        c.get("text")
                        or c.get("message")
                        or c.get("body")
                        or c.get("caption")
                    )
                else:
                    txt = ""
                if txt:
                    comments.append(txt)
        return comments

    @staticmethod
    def _extract_author(post: dict[str, Any]) -> str:
        """Trích username tác giả."""
        p = post.get("thread") or post
        author = (
            p.get("user")
            or p.get("username")
            or p.get("userName")
            or p.get("author")
            or ""
        )
        if isinstance(author, dict):
            author = author.get("username") or author.get("name") or ""
        return str(author).strip()

    def _format_output(self, posts: list[dict[str, Any]], limit: int | None = None) -> str:
        """
        Format list posts thành JSON string cho IntentAgent.
        Nếu `limit` được set, chỉ giữ tối đa `limit` bài.
        """
        import json
        if not posts:
            return "[]"
            
        cleaned_posts = []
        seen_urls: set[str] = set()
        
        for post in posts:
            if limit is not None and len(cleaned_posts) >= limit:
                break
            url = self._extract_url(post)
            text = self._extract_text(post)
            if not text:
                continue
            if url in seen_urls and url != "N/A":
                continue
            seen_urls.add(url)
            
            author = self._extract_author(post)
            comments = self._extract_comments(post)
            
            p = post.get("thread") or post
            cleaned_posts.append({
                "username": author,
                "isVerified": p.get("isVerified") or p.get("user_verified") or False,
                "captionText": text,
                "takenAtFormatted": p.get("takenAtFormatted") or str(p.get("published_on", "")),
                "likeCount": p.get("likeCount") or p.get("like_count") or 0,
                "directReplyCount": p.get("directReplyCount") or p.get("reply_count") or len(comments),
                "repostCount": p.get("repostCount") or 0,
                "postUrl": url,
                "comments": comments[:3]
            })
            
        return json.dumps(cleaned_posts, ensure_ascii=False, indent=2)
