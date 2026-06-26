"""
Crawl Router — API endpoint cho Facebook crawl pipeline.
POST /api/crawl/facebook
    → crawl Facebook → format content → chạy IntentAgent → trả intents
Luồng:
    1. Nhận keywords + config từ request body
    2. FacebookCrawler.run(keywords) → raw content string
    3. Set vào state.raw_input.content
    4. IntentAgent.run(state) → phân tích intents
    5. Trả kết quả (giống /api/discover)
"""
from __future__ import annotations
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from src.crawlers.facebook_crawler import FacebookCrawler
from src.crawlers.threads_crawler import ThreadsCrawler
from src.crawlers.tiktok_crawler import TiktokCrawler
from src.config import settings, BACKEND_DIR
from src.api.deps import get_state
from src.api.routers.frontend_api import (
    _map_pipeline_intents_to_fe,
    _get_model,
    _resolve_api_key,
)
from src.llm.factory import create_llm_client
from src.models.schemas import Intent, RawInput
from src.pipeline.intent_extractor import IntentAgent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/crawl", tags=["crawl"])

# ---------------------------------------------------------------------------
# Crawl history persistence — file JSON tích lũy dữ liệu (KHÔNG xóa log cũ).
# Mỗi lần crawl (facebook/threads/tiktok) sẽ append 1 "run" mới lên ĐẦU file,
# tương tự cách sheet ở FE cộng dồn kết quả lên đầu — vì mỗi lần crawl có thể
# ra kết quả khác nhau và ta muốn giữ lại toàn bộ lịch sử.
# ---------------------------------------------------------------------------
CRAWL_HISTORY_PATH = os.path.join(BACKEND_DIR, "data", "crawl_history.json")


def _load_crawl_history() -> list[dict]:
    """Dọc toàn bộ lịch sử crawl đã lưu trên đĩa. Không tồn tại/lỗi → trả về []."""
    try:
        if os.path.exists(CRAWL_HISTORY_PATH):
            with open(CRAWL_HISTORY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Không đọc được crawl_history.json: %s", exc)
    return []


def _append_crawl_history(
    platform: str, domain: str, keywords: list[str], posts: list[dict]
) -> int:
    """Append kết quả crawl mới nhất lên ĐẦU lịch sử và lưu lại ra file JSON.

    Không xóa các run đã lưu trước đó — chỉ cộng dồn thêm. Trả về tổng số
    posts đã tích lũy qua tất cả các lần crawl, để show trong crawl_logs.
    """
    history = _load_crawl_history()
    run_entry = {
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform,
        "domain": domain,
        "keywords": keywords,
        "post_count": len(posts),
        "posts": posts,
    }
    history = [run_entry] + history  # run mới nhất luôn ở đầu, log cũ giữ nguyên phía dưới
    try:
        os.makedirs(os.path.dirname(CRAWL_HISTORY_PATH), exist_ok=True)
        with open(CRAWL_HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        logger.warning("Không lưu được crawl_history.json: %s", exc)
    return sum(len(run.get("posts", [])) for run in history)


# ---------------------------------------------------------------------------
# Shared: run IntentAgent on crawled content, FE-map + persist to PipelineState
# ---------------------------------------------------------------------------
async def _mine_and_store(
    raw_content: str,
    domain: str,
    platform: str,
    keywords: list[str],
    source_type: str = "text",
) -> tuple[list[dict], list[str]]:
    """Mine intents from crawled content, FE-map + store in state (like /api/discover).

    Returns (fe_intents_dumped, crawl_logs). Never raises — degrades to empty
    intents so the crawl endpoint can still return raw content on LLM failure.
    """
    crawl_logs: list[str] = [
        f"Platform: {platform}",
        f"Keywords: {', '.join(keywords) if keywords else '(none)'}",
        f"Raw content length: {len(raw_content)} chars",
    ]
    if not raw_content.strip():
        crawl_logs.append("No content crawled — returning empty intents.")
        return [], crawl_logs

    try:
        model = _get_model()
        api_key = _resolve_api_key(model)
        llm = create_llm_client(model, api_key)
        agent = IntentAgent(llm, max_chunk_tokens=settings.chunk_max_tokens)
        raw_input = RawInput(content=raw_content, domain=domain, source_type=source_type)
        results = await agent.run(raw_input)
    except Exception as exc:
        logger.warning("IntentAgent failed: %s — returning raw content only.", exc)
        crawl_logs.append(f"IntentAgent skipped/failed: {exc}")
        return [], crawl_logs

    fe_intents = _map_pipeline_intents_to_fe(results)
    state = get_state()
    state.raw_input = raw_input
    state.intents = fe_intents
    state.internal_intents = [Intent(**r) for r in results]
    crawl_logs.append(f"Extracted {len(fe_intents)} intents from crawled content.")
    return [i.model_dump() for i in fe_intents], crawl_logs


def _parse_posts(raw_content: str, platform: str) -> list[dict]:
    """Parse the crawler's JSON output into normalized rows for the FE results table.

    All crawlers emit json.dumps of objects with keys: username, captionText,
    takenAtFormatted, likeCount, directReplyCount, postUrl, comments. Tolerant of
    empty/non-JSON content → returns [].
    """
    try:
        items = json.loads(raw_content)
    except (ValueError, TypeError):
        return []
    if not isinstance(items, list):
        return []
    posts: list[dict] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        posts.append({
            "platform": platform,
            "url": it.get("postUrl") or it.get("url") or "",
            "postingDate": it.get("takenAtFormatted") or "",
            "text": it.get("captionText") or it.get("text") or "",
            "likes": it.get("likeCount") or 0,
            "commentsCount": it.get("directReplyCount") or 0,
        })
    return posts
# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class FacebookCrawlRequest(BaseModel):
    """Request body cho POST /api/crawl/facebook."""
    platform: str = Field(default="facebook", description="Platform identifier")
    domain: str = Field(default="", description="Business domain / ngành hàng")
    keywords: list[str] = Field(..., min_length=1, description="Danh sách keywords cần crawl")
    # Apify config — override từ request, fallback sang .env
    apify_token: Optional[str] = Field(default=None, description="Apify API token")
    autocomplete_limit: int = Field(default=5, ge=1, le=20)
    search_limit: int = Field(default=20, ge=1, le=50)
    posts_limit: int = Field(default=20, ge=1, le=50)
    # LLM config — cho IntentAgent
    model: Optional[str] = Field(default=None, description="LLM model name")
    api_key: Optional[str] = Field(default=None, description="LLM API key")
    # Crawl-only by default; intents come from /api/discover. Set True for legacy behavior.
    extract_intents: bool = Field(default=False, description="Run IntentAgent on crawled content")
class FacebookCrawlResponse(BaseModel):
    """Response cho crawl endpoint."""
    success: bool
    platform: str
    keywords: list[str]
    raw_content_preview: str = Field(description="Preview 500 ký tự đầu của raw content")
    raw_content_length: int = Field(description="Tổng số ký tự raw content")
    raw_content: str = Field(description="Toàn bộ raw content đã crawl")
    crawl_posts: list[dict] = Field(default_factory=list, description="Normalized posts cho FE table")
    intents: Optional[list] = Field(default=None, description="Intents từ IntentAgent (nếu có)")
    crawl_logs: list[str] = Field(default_factory=list, description="Trace log của crawl pipeline")
    error: Optional[str] = None
class ThreadsCrawlRequest(BaseModel):
    """Request body cho POST /api/crawl/threads."""
    platform: str = Field(default="threads", description="Platform identifier")
    domain: str = Field(default="", description="Business domain / ngành hàng")
    keywords: list[str] = Field(..., min_length=1, description="Danh sách keywords cần crawl")
    # Apify config — override từ request, fallback sang .env
    apify_token: Optional[str] = Field(default=None, description="Apify API token")
    autocomplete_limit: int = Field(default=5, ge=1, le=20)
    search_limit: int = Field(default=20, ge=1, le=50)
    posts_limit: int = Field(default=20, ge=1, le=50)
    # LLM config — cho IntentAgent
    model: Optional[str] = Field(default=None, description="LLM model name")
    api_key: Optional[str] = Field(default=None, description="LLM API key")
    # Crawl-only by default; intents come from /api/discover. Set True for legacy behavior.
    extract_intents: bool = Field(default=False, description="Run IntentAgent on crawled content")

class ThreadsCrawlResponse(BaseModel):
    """Response cho crawl endpoint."""
    success: bool
    platform: str
    keywords: list[str]
    raw_content_preview: str = Field(description="Preview 500 ký tự đầu của raw content")
    raw_content_length: int = Field(description="Tổng số ký tự raw content")
    raw_content: str = Field(description="Toàn bộ raw content đã crawl")
    crawl_posts: list[dict] = Field(default_factory=list, description="Normalized posts cho FE table")
    intents: Optional[list] = Field(default=None, description="Intents từ IntentAgent (nếu có)")
    crawl_logs: list[str] = Field(default_factory=list, description="Trace log của crawl pipeline")
    error: Optional[str] = None

class TiktokCrawlRequest(BaseModel):
    """Request body cho POST /api/crawl/tiktok."""
    platform: str = Field(default="tiktok", description="Platform identifier")
    domain: str = Field(default="", description="Business domain / ngành hàng")
    keywords: list[str] = Field(..., min_length=1, description="Danh sách keywords cần crawl")
    apify_token: Optional[str] = Field(default=None, description="Apify API token")
    search_limit: int = Field(default=20, ge=1, le=50)
    model: Optional[str] = Field(default=None, description="LLM model name")
    api_key: Optional[str] = Field(default=None, description="LLM API key")
    # Crawl-only by default; intents come from /api/discover. Set True for legacy behavior.
    extract_intents: bool = Field(default=False, description="Run IntentAgent on crawled content")

class TiktokCrawlResponse(BaseModel):
    """Response cho tiktok crawl endpoint."""
    success: bool
    platform: str
    keywords: list[str]
    raw_content_preview: str = Field(description="Preview 500 ký tự đầu của raw content")
    raw_content_length: int = Field(description="Tổng số ký tự raw content")
    raw_content: str = Field(description="Toàn bộ raw content đã crawl")
    crawl_posts: list[dict] = Field(default_factory=list, description="Normalized posts cho FE table")
    intents: Optional[list] = Field(default=None, description="Intents từ IntentAgent (nếu có)")
    crawl_logs: list[str] = Field(default_factory=list, description="Trace log của crawl pipeline")
    error: Optional[str] = None

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/facebook", response_model=FacebookCrawlResponse)
async def crawl_facebook(req: FacebookCrawlRequest) -> FacebookCrawlResponse:
    """
    Crawl Facebook qua Apify → trả raw content (+ optional IntentAgent analysis).
    """
    # ---- Resolve Apify token ----
    token = req.apify_token or getattr(settings, "apify_token", "") or ""
    if not token:
        raise HTTPException(
            status_code=400,
            detail="apify_token is required — gửi trong request body hoặc set APIFY_TOKEN trong .env",
        )
    # ---- Crawl ----
    try:
        crawler = FacebookCrawler(
            apify_token=token,
            autocomplete_limit=req.autocomplete_limit,
            search_limit=req.search_limit,
            posts_limit=req.posts_limit,
        )
        raw_content = await crawler.run(keywords=req.keywords)
    except Exception as exc:
        logger.exception("Crawl failed")
        return FacebookCrawlResponse(
            success=False,
            platform=req.platform,
            keywords=req.keywords,
            raw_content_preview="",
            raw_content_length=0,
            raw_content="",
            error=f"Crawl error: {exc}",
        )
    # ---- Store crawled content for later /api/discover; optionally mine intents now ----
    get_state().raw_social_content = raw_content
    crawl_posts = _parse_posts(raw_content, req.platform)
    # Lưu lịch sử crawl ra file JSON — append lên đầu, KHÔNG xóa các lần crawl trước.
    total_saved = _append_crawl_history(req.platform, req.domain, req.keywords, crawl_posts)
    if req.extract_intents:
        intents, crawl_logs = await _mine_and_store(
            raw_content, req.domain, req.platform, req.keywords
        )
    else:
        intents, crawl_logs = [], [
            f"Platform: {req.platform}",
            f"Crawled {len(crawl_posts)} posts (crawl-only, intents skipped).",
        ]
    crawl_logs.append(
        f"Saved to data/crawl_history.json — accumulated total: {total_saved} posts across all runs (old logs kept)."
    )
    # ---- Response ----
    return FacebookCrawlResponse(
        success=True,
        platform=req.platform,
        keywords=req.keywords,
        raw_content_preview=raw_content[:500],
        raw_content_length=len(raw_content),
        raw_content=raw_content,
        crawl_posts=crawl_posts,
        intents=intents,
        crawl_logs=crawl_logs,
    )
@router.post("/threads", response_model=ThreadsCrawlResponse)
async def crawl_threads(req: ThreadsCrawlRequest) -> ThreadsCrawlResponse:
    """
    Crawl Threads qua Apify → trả raw content (+ optional IntentAgent analysis).
    """
    # ---- Resolve Apify token ----
    token = req.apify_token or getattr(settings, "apify_token", "") or ""
    if not token:
        raise HTTPException(
            status_code=400,
            detail="apify_token is required — gửi trong request body hoặc set APIFY_TOKEN trong .env",
        )
    # ---- Crawl ----
    try:
        crawler = ThreadsCrawler(
            apify_token=token,
            autocomplete_limit=req.autocomplete_limit,
            search_limit=req.search_limit,
            posts_limit=req.posts_limit,
        )
        raw_content = await crawler.run(keywords=req.keywords)
    except Exception as exc:
        logger.exception("Crawl failed")
        return ThreadsCrawlResponse(
            success=False,
            platform=req.platform,
            keywords=req.keywords,
            raw_content_preview="",
            raw_content_length=0,
            raw_content="",
            error=f"Crawl error: {exc}",
        )
    # ---- Store crawled content for later /api/discover; optionally mine intents now ----
    get_state().raw_social_content = raw_content
    crawl_posts = _parse_posts(raw_content, req.platform)
    # Lưu lịch sử crawl ra file JSON — append lên đầu, KHÔNG xóa các lần crawl trước.
    total_saved = _append_crawl_history(req.platform, req.domain, req.keywords, crawl_posts)
    if req.extract_intents:
        intents, crawl_logs = await _mine_and_store(
            raw_content, req.domain, req.platform, req.keywords
        )
    else:
        intents, crawl_logs = [], [
            f"Platform: {req.platform}",
            f"Crawled {len(crawl_posts)} posts (crawl-only, intents skipped).",
        ]
    crawl_logs.append(
        f"Saved to data/crawl_history.json — accumulated total: {total_saved} posts across all runs (old logs kept)."
    )
    # ---- Response ----
    return ThreadsCrawlResponse(
        success=True,
        platform=req.platform,
        keywords=req.keywords,
        raw_content_preview=raw_content[:500],
        raw_content_length=len(raw_content),
        raw_content=raw_content,
        crawl_posts=crawl_posts,
        intents=intents,
        crawl_logs=crawl_logs,
    )

# ---------------------------------------------------------------------------
# TikTok Endpoint
# ---------------------------------------------------------------------------
@router.post("/tiktok", response_model=TiktokCrawlResponse)
async def crawl_tiktok(req: TiktokCrawlRequest) -> TiktokCrawlResponse:
    """
    Crawl TikTok qua Apify → trả raw content (+ optional IntentAgent analysis).
    """
    token = req.apify_token or getattr(settings, "apify_token", "") or ""
    if not token:
        raise HTTPException(
            status_code=400,
            detail="apify_token is required — gửi trong request body hoặc set APIFY_TOKEN trong .env",
        )
    try:
        crawler = TiktokCrawler(
            apify_token=token,
            search_limit=req.search_limit,
        )
        raw_content = await crawler.run(keywords=req.keywords)
    except Exception as exc:
        logger.exception("Crawl failed")
        return TiktokCrawlResponse(
            success=False,
            platform=req.platform,
            keywords=req.keywords,
            raw_content_preview="",
            raw_content_length=0,
            raw_content="",
            error=f"Crawl error: {exc}",
        )
    
    # ---- Store crawled content for later /api/discover; optionally mine intents now ----
    get_state().raw_social_content = raw_content
    crawl_posts = _parse_posts(raw_content, req.platform)
    # Lưu lịch sử crawl ra file JSON — append lên đầu, KHÔNG xóa các lần crawl trước.
    total_saved = _append_crawl_history(req.platform, req.domain, req.keywords, crawl_posts)
    if req.extract_intents:
        intents, crawl_logs = await _mine_and_store(
            raw_content, req.domain, req.platform, req.keywords, source_type="tiktok"
        )
    else:
        intents, crawl_logs = [], [
            f"Platform: {req.platform}",
            f"Crawled {len(crawl_posts)} posts (crawl-only, intents skipped).",
        ]
    crawl_logs.append(
        f"Saved to data/crawl_history.json — accumulated total: {total_saved} posts across all runs (old logs kept)."
    )
    return TiktokCrawlResponse(
        success=True,
        platform=req.platform,
        keywords=req.keywords,
        raw_content_preview=raw_content[:500],
        raw_content_length=len(raw_content),
        raw_content=raw_content,
        crawl_posts=crawl_posts,
        intents=intents,
        crawl_logs=crawl_logs,
    )

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@router.get("/health")
async def crawl_health():
    """Kiểm tra crawl module hoạt động."""
    return {"status": "ok", "module": "crawl", "supported_platforms": ["facebook", "threads", "tiktok"]}
