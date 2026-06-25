"""
FacebookCrawler — crawl Facebook qua 3 Apify actors theo pipeline:
    1. Google Autocomplete  →  mở rộng keywords thành nhiều search queries
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
# Actor IDs (Apify Store)
# ---------------------------------------------------------------------------
AUTOCOMPLETE_ACTOR = "dainins/google-autocomplete-scraper"
SEARCH_ACTOR = "alien_force/facebook-search-scraper"
POSTS_ACTOR = "apify/facebook-posts-scraper"
class FacebookCrawler(BaseCrawler):
    """Pipeline crawl Facebook: autocomplete → search → scrape."""
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
        Gọi Google Autocomplete Scraper để mở rộng 1 keyword
        thành nhiều search queries.
        Actor: dainins/google-autocomplete-scraper
        Input schema:
            {
                "queries": ["keyword"],
                "maxResults": 5,
                "languageCode": "vi",
                "countryCode": "vn"
            }
        Output: [{"query": "...", "results": ["suggestion1", ...]}]
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
        # Parse suggestions — thử nhiều field names để đảm bảo tương thích
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
    # Step 2 — Facebook Search Posts
    # ==================================================================
    async def search_posts(
        self,
        query: str,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Tìm bài viết Facebook bằng keyword.
        Actor: alien_force/facebook-search-scraper
        Input schema:
            {
                "keyword": "search query",
                "search_type": "posts",
                "max_posts": 5
            }
        Output: list of post objects (có url, text, author…)
        """
        limit = limit or self.search_limit
        run_input: dict[str, Any] = {
            "keyword": query,
            "search_type": "posts",
            "max_posts": limit,
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
        Input schema:
            {
                "startUrls": [{"url": "https://..."}],
                "resultsLimit": 5
            }
        Output: list of post objects với text, comments, likes …
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
    # ==================================================================
    # Orchestrator — chạy toàn bộ pipeline
    # ==================================================================
    async def run(self, keywords: list[str]) -> str:
        """
        Full pipeline:
            keywords → autocomplete → search → scrape → formatted string
        Nếu Step 3 (scrape_posts) không trả kết quả, fallback sang
        content từ Step 2 (search_posts) — vì search thường đã có text.
        """
        all_posts: list[dict[str, Any]] = []
        for keyword in keywords:
            logger.info("=" * 60)
            logger.info("Processing keyword: '%s'", keyword)
            # ---- Step 1: Không dùng Autocomplete để tiết kiệm chi phí Apify ----
            queries = [keyword]
            # ---- Step 2: Search Facebook cho mỗi query ----
            search_results: list[dict[str, Any]] = []
            for query in queries:
                results = await self.search_posts(query)
                search_results.extend(results)
            if not search_results:
                logger.warning("No search results for keyword '%s' — skipping.", keyword)
                continue
            # ---- Thu thập URLs từ search results ----
            urls: list[str] = []
            for item in search_results:
                url = (
                    item.get("url")
                    or item.get("postUrl")
                    or item.get("link")
                    or ""
                )
                if url and url.startswith("http") and url not in urls:
                    urls.append(url)
            # ---- Step 3: Deep scrape posts ----
            if urls:
                scraped = await self.scrape_posts(urls)
                if scraped:
                    all_posts.extend(scraped)
                    continue   # deep scrape thành công → dùng data này
            # ---- Fallback: dùng search results nếu scrape trống ----
            logger.info("Falling back to search results for keyword '%s'.", keyword)
            all_posts.extend(search_results)
        # ---- Format output ----
        return self._format_output(all_posts)
    # ==================================================================
    # Format helpers
    # ==================================================================
    @staticmethod
    def _extract_text(post: dict[str, Any]) -> str:
        """Trích text chính từ post — thử nhiều field names."""
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
        """Trích URL từ post."""
        return (
            post.get("url")
            or post.get("postUrl")
            or post.get("link")
            or post.get("permalink")
            or "N/A"
        )
    @staticmethod
    def _extract_comments(post: dict[str, Any]) -> list[str]:
        """Trích danh sách comment texts từ post."""
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
        """Trích tên tác giả."""
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
            # Skip bài trùng URL hoặc rỗng nội dung
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
                "comments": comments[:3]
            })
            
        return json.dumps(cleaned_posts, ensure_ascii=False, indent=2)
