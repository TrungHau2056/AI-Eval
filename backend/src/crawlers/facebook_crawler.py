"""
FacebookCrawler — crawl Facebook qua 3 Apify actors theo pipeline:
    1. Google Autocomplete  →  mở rộng keywords thành nhiều search queries
    2. Facebook Search      →  tìm bài viết Facebook theo từng query
    3. Facebook Posts       →  scrape nội dung đầy đủ từ các URLs
Output là JSON chứa danh sách bài viết đã được làm sạch 
(chỉ giữ lại link, liked, content) để tối ưu input cho AI (IntentAgent).
Actor schemas verified từ Apify docs chính thức.
"""
from __future__ import annotations
import json
import logging
from typing import Any
from src.crawlers.base import BaseCrawler
logger = logging.getLogger(__name__)
# ---------------------------------------------------------------------------
# Actor IDs — dùng ~ separator cho Apify REST API
# ---------------------------------------------------------------------------
AUTOCOMPLETE_ACTOR = "automation-lab~google-autocomplete-scraper"
SEARCH_ACTOR = "scraper_one~facebook-posts-search"
POSTS_ACTOR = "apify~facebook-posts-scraper"
class FacebookCrawler(BaseCrawler):
    """Pipeline crawl Facebook: autocomplete → search → scrape."""
    def __init__(
        self,
        apify_token: str,
        autocomplete_limit: int = 5,
        search_limit: int = 20,       # Tăng limit để đạt coverage lớn
        posts_limit: int = 20,
    ) -> None:
        super().__init__(apify_token)
        self.autocomplete_limit = autocomplete_limit
        self.search_limit = max(search_limit, 10)
        self.posts_limit = posts_limit
    # ==================================================================
    # Step 1 — Google Autocomplete
    # ==================================================================
    async def get_autocomplete(
        self,
        keyword: str,
        limit: int | None = None,
    ) -> list[str]:
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
            text = item.get("suggestion", "").strip()
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
        limit = max(limit or self.search_limit, 10)
        run_input: dict[str, Any] = {
            "query": query,
            "resultsCount": limit,
            "searchType": "top"
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
        if not urls:
            return []
        start_urls = [{"url": u} for u in urls]
        run_input: dict[str, Any] = {
            "startUrls": start_urls,
            "resultsLimit": self.posts_limit * len(urls),
        }
        try:
            # Chờ lâu hơn vì loop qua nhiều URLs sẽ mất thời gian
            items = await self._run_actor(POSTS_ACTOR, run_input, wait_secs=900)
        except Exception as exc:
            logger.error("Scrape posts failed: %s", exc)
            return []
        valid_items = [i for i in items if "error" not in i]
        logger.info("Scraped %d valid posts from %d URLs.", len(valid_items), len(urls))
        return valid_items
    # ==================================================================
    # Orchestrator — chạy toàn bộ pipeline
    # ==================================================================
    async def run(self, keywords: list[str]) -> str:
        """
        Full pipeline:
            keywords → autocomplete → search → scrape → clean_data → JSON string
        Đảm bảo loop hết qua toàn bộ links để đạt coverage lớn nhất.
        """
        all_urls: list[str] = []
        fallback_search_items: list[dict[str, Any]] = []
        for keyword in keywords:
            logger.info("=" * 60)
            logger.info("Processing keyword: '%s'", keyword)
            # ---- Step 1: Mở rộng keyword ----
            queries = await self.get_autocomplete(keyword)
            # ---- Step 2: Search Facebook cho TẤT CẢ queries ----
            for query in queries:
                search_results = await self.search_posts(query)
                fallback_search_items.extend(search_results)
                
                for item in search_results:
                    url = item.get("url") or item.get("post_url") or ""
                    if url.startswith("http") and url not in all_urls:
                        all_urls.append(url)
        if not all_urls:
            logger.warning("No search results found for any keywords.")
            return json.dumps([], ensure_ascii=False)
        logger.info("Total unique URLs found to scrape: %d", len(all_urls))
        # ---- Step 3: Deep scrape posts cho TOÀN BỘ URLs ----
        all_scraped_items = await self.scrape_posts(all_urls)
        # Fallback: Nếu scrape deep thất bại do rate limit, dùng luôn data từ bước search
        if not all_scraped_items and fallback_search_items:
            logger.info("Falling back to search results data due to empty scrape results.")
            all_scraped_items = fallback_search_items
        # ---- Format output ----
        cleaned_data = self._clean_data(all_scraped_items)
        return json.dumps(cleaned_data, indent=2, ensure_ascii=False)
    # ==================================================================
    # Data Cleaning (Chỉ giữ lại link, liked, content)
    # ==================================================================
    def _clean_data(self, raw_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Làm sạch JSON thô.
        Chỉ giữ lại đúng 3 trường: link, liked, content.
        """
        cleaned = []
        seen_urls = set()
        for item in raw_items:
            url = item.get("url") or item.get("facebookUrl") or ""
            content = item.get("text") or item.get("postText") or item.get("message") or ""
            liked = (
                item.get("reactionLikeCount") 
                or item.get("likesCount") 
                or item.get("topReactionsCount") 
                or item.get("reactionsCount") 
                or 0
            )
            
            content = content.strip()
            
            # Chỉ lấy bài viết thực sự có nội dung và tránh trùng lặp
            if url and content and url not in seen_urls:
                seen_urls.add(url)
                cleaned.append({
                    "link": url,
                    "liked": liked,
                    "content": content
                })
                
        logger.info("Cleaned data: %d items ready.", len(cleaned))
        return cleaned
