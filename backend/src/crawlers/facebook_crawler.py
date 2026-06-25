"""
FacebookCrawler — crawl Facebook qua 3 Apify actors theo pipeline:
    1. Google Autocomplete  →  mở rộng keywords thành nhiều search queries (optional)
    2. Facebook Search      →  tìm bài viết Facebook theo từng query
    3. Facebook Posts       →  scrape nội dung đầy đủ + comments từ URLs
Output là 1 string formatted sẵn sàng cho IntentAgent.
"""
from __future__ import annotations
import logging
from typing import Any
from src.crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Actor IDs (Apify Store) — pay-per-event, works on free plan credits
# ---------------------------------------------------------------------------
AUTOCOMPLETE_ACTOR = "automation-lab/google-autocomplete-scraper"
SEARCH_ACTOR = "scraper_one/facebook-posts-search"
POSTS_ACTOR = "apify/facebook-posts-scraper"


class FacebookCrawler(BaseCrawler):
    """Pipeline crawl Facebook: search → scrape (autocomplete optional)."""

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
    # Step 1 — Google Autocomplete (optional; disabled in run() by default)
    # ==================================================================
    async def get_autocomplete(
        self,
        keyword: str,
        limit: int | None = None,
    ) -> list[str]:
        """
        Gọi Google Autocomplete Scraper để mở rộng 1 keyword
        thành nhiều search queries.
        Actor: automation-lab/google-autocomplete-scraper
        """
        limit = limit or self.autocomplete_limit
        run_input: dict[str, Any] = {
            "keywords": [keyword],
            "language": "vi",
            "country": "vn",
            "maxDepth": 1,
            "maxSuggestionsPerKeyword": limit,
            "appendAlphabet": False,
        }
        try:
            items = await self._run_actor(AUTOCOMPLETE_ACTOR, run_input)
        except Exception as exc:
            logger.error("Autocomplete failed for '%s': %s", keyword, exc)
            return [keyword]

        suggestions: list[str] = []
        for item in items:
            if isinstance(item.get("suggestion"), str) and item["suggestion"]:
                text = item["suggestion"].strip()
                if text not in suggestions:
                    suggestions.append(text)
                continue
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
            suggestions = [keyword]
        logger.info("Autocomplete '%s' → %d queries: %s", keyword, len(suggestions), suggestions[:5])
        return suggestions[:limit]

    # ==================================================================
    # Step 2 — Facebook Search Posts
    # ==================================================================
    async def search_posts(
        self,
        query: str,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Tìm bài viết Facebook bằng keyword.
        Actor: scraper_one/facebook-posts-search
        """
        limit = limit or self.search_limit
        run_input: dict[str, Any] = {
            "query": query,
            "resultsCount": limit,
            "searchType": "top",
        }
        try:
            items = await self._run_actor(SEARCH_ACTOR, run_input)
        except Exception as exc:
            logger.error("Search failed for '%s': %s", query, exc)
            return []
        logger.info("Search '%s' → %d results.", query, len(items))
        return items

    # ==================================================================
    # Step 3 — Facebook Posts Scraper (deep scrape)
    # ==================================================================
    async def scrape_posts(
        self,
        urls: list[str],
    ) -> list[dict[str, Any]]:
        """
        Scrape nội dung đầy đủ (text + comments) từ list URLs.
        Actor: apify/facebook-posts-scraper
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
            logger.error("Scrape posts failed: %s", exc)
            return []
        logger.info("Scraped %d posts from %d URLs.", len(items), len(urls))
        return items

    @staticmethod
    def _extract_post_url(item: dict[str, Any]) -> str:
        return (
            item.get("url")
            or item.get("post_url")
            or item.get("postUrl")
            or item.get("link")
            or item.get("permalink")
            or ""
        )

    # ==================================================================
    # Orchestrator — chạy toàn bộ pipeline
    # ==================================================================
    async def run(self, keywords: list[str]) -> str:
        """
        Full pipeline:
            keywords → search → scrape → formatted string
        Autocomplete is skipped by default to save Apify cost.
        Nếu Step 3 (scrape_posts) không trả kết quả, fallback sang
        content từ Step 2 (search_posts).
        """
        all_posts: list[dict[str, Any]] = []
        for keyword in keywords:
            logger.info("=" * 60)
            logger.info("Processing keyword: '%s'", keyword)
            queries = [keyword]

            search_results: list[dict[str, Any]] = []
            for query in queries:
                results = await self.search_posts(query)
                search_results.extend(results)
            if not search_results:
                logger.warning("No search results for keyword '%s' — skipping.", keyword)
                continue

            urls: list[str] = []
            for item in search_results:
                url = self._extract_post_url(item)
                if url and url.startswith("http") and url not in urls:
                    urls.append(url)

            if urls:
                scraped = await self.scrape_posts(urls)
                if scraped:
                    all_posts.extend(scraped)
                    continue

            logger.info("Falling back to search results for keyword '%s'.", keyword)
            all_posts.extend(search_results)

        return self._format_output(all_posts)

    # ==================================================================
    # Format helpers
    # ==================================================================
    @staticmethod
    def _extract_text(post: dict[str, Any]) -> str:
        return (
            post.get("text")
            or post.get("postText")
            or post.get("message")
            or post.get("content")
            or post.get("body")
            or ""
        ).strip()

    @staticmethod
    def _extract_url(post: dict[str, Any]) -> str:
        url = FacebookCrawler._extract_post_url(post)
        return url or "N/A"

    @staticmethod
    def _extract_comments(post: dict[str, Any]) -> list[str]:
        comments_raw = post.get("comments") or post.get("topComments") or []
        comments: list[str] = []
        if isinstance(comments_raw, list):
            for c in comments_raw:
                if isinstance(c, str):
                    txt = c.strip()
                elif isinstance(c, dict):
                    txt = (
                        c.get("text")
                        or c.get("message")
                        or c.get("body")
                        or c.get("comment_text")
                        or ""
                    ).strip()
                else:
                    txt = ""
                if txt:
                    comments.append(txt)
        return comments

    @staticmethod
    def _extract_author(post: dict[str, Any]) -> str:
        author = (
            post.get("user")
            or post.get("userName")
            or post.get("author")
            or post.get("pageName")
            or ""
        )
        if isinstance(author, dict):
            author = author.get("name") or author.get("username") or ""
        return str(author).strip()

    def _format_output(self, posts: list[dict[str, Any]]) -> str:
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
            comments = self._extract_comments(post)

            cleaned_posts.append({
                "username": author,
                "isVerified": post.get("isVerified") or post.get("verified") or False,
                "captionText": text,
                "takenAtFormatted": post.get("time") or post.get("date") or "",
                "likeCount": post.get("likes") or post.get("likeCount") or 0,
                "directReplyCount": post.get("comments") or len(comments),
                "repostCount": post.get("shares") or post.get("shareCount") or 0,
                "postUrl": url,
                "comments": comments[:3],
            })

        return json.dumps(cleaned_posts, ensure_ascii=False, indent=2)
