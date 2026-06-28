"""
FacebookCrawler — crawl Facebook qua 3 Apify actors theo pipeline:
    1. Google Autocomplete  →  mở rộng keywords thành nhiều search queries (optional)
    2. Facebook Search      →  tìm bài viết Facebook theo từng query
    3. Facebook Posts       →  scrape nội dung đầy đủ + comments từ URLs
Output là 1 string formatted sẵn sàng cho IntentAgent.
"""
from __future__ import annotations
import logging
import json
from datetime import datetime, timezone
from typing import Any
from src.crawlers.base import BaseCrawler, coerce_text

logger = logging.getLogger(__name__)

# Search actor chain:
#   1. scrapeforge/facebook-search-posts (primary)
#   2. igview-owner/facebook-old-posts-search (fallback when primary returns 0 rows)
#   3. scraper_one/facebook-posts-search (legacy fallback)
SEARCH_ACTOR = "scrapeforge/facebook-search-posts"
FALLBACK_SEARCH_ACTOR = "igview-owner/facebook-old-posts-search"
LEGACY_SEARCH_ACTOR = "scraper_one/facebook-posts-search"
POSTS_ACTOR = "apify/facebook-posts-scraper"
AUTOCOMPLETE_ACTOR = "automation-lab/google-autocomplete-scraper"


class FacebookCrawler(BaseCrawler):
    """Pipeline crawl Facebook: search → scrape (autocomplete optional)."""

    def __init__(
        self,
        apify_token: str,
        autocomplete_limit: int = 5,
        search_limit: int = 2,
        posts_limit: int = 2,
    ) -> None:
        super().__init__(apify_token)
        self.autocomplete_limit = autocomplete_limit
        self.search_limit = search_limit
        self.posts_limit = posts_limit

    async def get_autocomplete(
        self,
        keyword: str,
        limit: int | None = None,
    ) -> list[str]:
        """Gọi automation-lab/google-autocomplete-scraper để mở rộng keyword."""
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
                    text = coerce_text(r) if not isinstance(r, str) else r.strip()
                    if text and text not in suggestions:
                        suggestions.append(text)

        if not suggestions:
            suggestions = [keyword]
        logger.info("Autocomplete '%s' → %d queries: %s", keyword, len(suggestions), suggestions[:5])
        return suggestions[:limit]

    async def search_posts(
        self,
        query: str,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Search Facebook posts — primary actor, then igview fallback, then legacy."""
        limit = limit or self.search_limit

        try:
            items = await self._run_actor(SEARCH_ACTOR, {
                "query": query,
                "maxResults": limit,
            })
            filtered = self._filter_search_items(items)
            if filtered:
                logger.info("Primary search '%s' → %d results.", query, len(filtered))
                return filtered
        except Exception as exc:
            logger.error("Primary search failed for '%s': %s", query, exc)

        logger.warning(
            "Primary search actor returned 0 rows for '%s' — trying igview fallback.",
            query,
        )
        fallback = self._filter_search_items(await self._igview_search_posts(query, limit))
        if fallback:
            logger.info("Igview fallback search '%s' → %d results.", query, len(fallback))
            return fallback

        logger.warning(
            "Igview fallback returned 0 rows for '%s' — trying legacy actor.",
            query,
        )
        legacy = self._filter_search_items(await self._legacy_search_posts(query, limit))
        if legacy:
            logger.info("Legacy search '%s' → %d results.", query, len(legacy))
        else:
            logger.warning("All search actors returned 0 rows for '%s'.", query)
        return legacy

    async def _igview_search_posts(self, query: str, limit: int) -> list[dict[str, Any]]:
        """Fallback search via igview-owner/facebook-old-posts-search."""
        run_input: dict[str, Any] = {
            "query": query,
            "maxResults": limit,
        }
        try:
            return await self._run_actor(FALLBACK_SEARCH_ACTOR, run_input)
        except Exception as exc:
            logger.error("Igview fallback search failed for '%s': %s", query, exc)
            return []

    async def _legacy_search_posts(self, query: str, limit: int) -> list[dict[str, Any]]:
        run_input: dict[str, Any] = {
            "query": query,
            "search_type": "posts",
            "max_results": min(limit, 200),
            "recent_posts": False,
        }
        try:
            return await self._run_actor(LEGACY_SEARCH_ACTOR, run_input)
        except Exception as exc:
            logger.error("Legacy search failed for '%s': %s", query, exc)
            return []

    @staticmethod
    def _filter_search_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        valid: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict) or item.get("error"):
                continue
            if FacebookCrawler._extract_post_url(item):
                valid.append(item)
        return valid

    async def scrape_posts(
        self,
        urls: list[str],
    ) -> list[dict[str, Any]]:
        """Scrape nội dung đầy đủ từ URLs qua apify/facebook-posts-scraper."""
        if not urls:
            return []
        run_input: dict[str, Any] = {
            "startUrls": [{"url": u} for u in urls],
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
            or item.get("facebookUrl")
            or item.get("link")
            or item.get("permalink")
            or ""
        )

    @staticmethod
    def _attachment_caption(item: dict[str, Any]) -> str:
        attachments = item.get("attachments")
        if not isinstance(attachments, list):
            return ""
        for att in attachments:
            if not isinstance(att, dict):
                continue
            caption = att.get("accessibilityCaption") or att.get("title") or att.get("description")
            if isinstance(caption, str) and caption.strip():
                return caption.strip()
        return ""

    async def run(self, keywords: list[str]) -> str:
        """
        keywords → search → scrape → formatted string.
        Autocomplete skipped by default to save Apify cost.
        """
        all_posts: list[dict[str, Any]] = []
        for keyword in keywords:
            logger.info("=" * 60)
            logger.info("Processing keyword: '%s'", keyword)
            queries = [keyword]

            search_results: list[dict[str, Any]] = []
            for query in queries:
                search_results.extend(await self.search_posts(query))
            if not search_results:
                logger.warning("No search results for keyword '%s' — skipping.", keyword)
                continue

            posts_with_text = [item for item in search_results if self._extract_text(item)]
            if posts_with_text:
                all_posts.extend(posts_with_text)
                continue

            urls: list[str] = []
            for item in search_results:
                url = self._extract_post_url(item)
                if url and url.startswith("http") and url not in urls:
                    urls.append(url)

            urls = urls[: self.posts_limit]

            if urls:
                scraped = self._filter_search_items(await self.scrape_posts(urls))
                if scraped:
                    all_posts.extend(scraped)
                    continue

            logger.info("Falling back to search results for keyword '%s'.", keyword)
            all_posts.extend(search_results)

        return self._format_output(all_posts)

    def _filter_usable_posts(self, posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Bỏ item lỗi / không có text (vd. apify/facebook-posts-scraper trả error object)."""
        usable: list[dict[str, Any]] = []
        for post in posts:
            if post.get("error"):
                continue
            if self._extract_text(post):
                usable.append(post)
        return usable

    @staticmethod
    def _extract_text(post: dict[str, Any]) -> str:
        for key in ("text", "postText", "message", "message_rich", "content", "body"):
            text = coerce_text(post.get(key))
            if text:
                return text
        return FacebookCrawler._attachment_caption(post)

    @staticmethod
    def _extract_url(post: dict[str, Any]) -> str:
        url = FacebookCrawler._extract_post_url(post)
        return url or "N/A"

    @staticmethod
    def _extract_comments(post: dict[str, Any]) -> list[str]:
        comments_raw = post.get("comments") or post.get("topComments") or []
        if isinstance(comments_raw, int):
            return []
        comments: list[str] = []
        if isinstance(comments_raw, list):
            for c in comments_raw:
                if isinstance(c, str):
                    txt = c.strip()
                elif isinstance(c, dict):
                    txt = coerce_text(
                        c.get("text")
                        or c.get("message")
                        or c.get("body")
                        or c.get("comment_text")
                    )
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
            or post.get("author_title")
            or ""
        )
        if isinstance(author, dict):
            author = author.get("name") or author.get("username") or ""
        return str(author).strip()

    @staticmethod
    def _extract_like_count(post: dict[str, Any]) -> int:
        reactions = post.get("reactions")
        if isinstance(reactions, dict) and reactions.get("like") is not None:
            return int(reactions["like"])
        for key in (
            "reactions_count",
            "reactionsCount",
            "likes",
            "likeCount",
            "reactionLikeCount",
            "likesCount",
        ):
            val = post.get(key)
            if val is not None:
                return int(val)
        return 0

    @staticmethod
    def _extract_reply_count(post: dict[str, Any]) -> int:
        comments = post.get("comments")
        if isinstance(comments, int):
            return comments
        for key in ("comments_count", "commentsCount", "commentCount", "directReplyCount"):
            val = post.get(key)
            if val is not None:
                return int(val)
        return len(FacebookCrawler._extract_comments(post))

    @staticmethod
    def _extract_share_count(post: dict[str, Any]) -> int:
        for key in ("reshare_count", "sharesCount", "shareCount", "shares", "repostCount"):
            val = post.get(key)
            if val is not None:
                return int(val)
        return 0

    @staticmethod
    def _extract_post_date(post: dict[str, Any]) -> str:
        for key in ("time", "date", "takenAtFormatted"):
            val = post.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        ts = post.get("timestamp")
        if isinstance(ts, (int, float)) and ts > 0:
            return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        return ""

    def _format_output(self, posts: list[dict[str, Any]], limit: int | None = None) -> str:
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

            cleaned_posts.append({
                "username": author,
                "isVerified": post.get("isVerified") or post.get("verified") or False,
                "captionText": text,
                "takenAtFormatted": self._extract_post_date(post),
                "likeCount": self._extract_like_count(post),
                "directReplyCount": self._extract_reply_count(post),
                "repostCount": self._extract_share_count(post),
                "postUrl": url,
                "comments": comments[:3],
            })

        if posts and not cleaned_posts:
            logger.warning(
                "Facebook formatter dropped %d raw item(s) — no text in known fields.",
                len(posts),
            )

        return json.dumps(cleaned_posts, ensure_ascii=False, indent=2)
