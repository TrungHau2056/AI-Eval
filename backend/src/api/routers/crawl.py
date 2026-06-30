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
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from src.crawlers.facebook_crawler import FacebookCrawler
from src.crawlers.threads_crawler import ThreadsCrawler
from src.crawlers.tiktok_crawler import TiktokCrawler
from src.crawlers.crawl_store import clear_posts, load_posts, save_posts
from src.crawlers.crawl_persist import persist_crawl_posts, sync_social_content_to_state
from src.config import settings
from src.api.deps import get_state
from src.api.routers.frontend_api import (
    _map_pipeline_intents_to_fe,
    _get_model,
    _resolve_api_key,
)
from src.llm.factory import create_llm_client
from src.models.schemas import Intent, RawInput
from src.observability.costs import cost_operation, summarize_run
from src.pipeline.intent_extractor import IntentAgent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/crawl", tags=["crawl"])


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


def _normalize_keywords(keywords: list[str]) -> list[str]:
    """Strip hashtag markers and underscores so crawlers receive plain search terms."""
    seen: set[str] = set()
    normalized: list[str] = []
    for kw in keywords:
        clean = " ".join(kw.replace("#", "").replace("_", " ").split()).strip()
        if clean and clean not in seen:
            seen.add(clean)
            normalized.append(clean)
    return normalized


def _crawl_logs(
    platform: str,
    keywords: list[str],
    new_count: int,
    total_count: int,
) -> list[str]:
    logs = [
        f"Platform: {platform}",
        f"Keywords: {', '.join(keywords) if keywords else '(none)'}",
        f"Crawled {new_count} new posts; {total_count} total in sheet (crawl-only, intents skipped).",
    ]
    if new_count == 0:
        logs.append("No posts found — try different keywords or check Apify actor limits.")
    return logs
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
    search_limit: int = Field(default=2, ge=1, le=50)
    posts_limit: int = Field(default=2, ge=1, le=50)
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
    crawl_posts: list[dict] = Field(default_factory=list, description="All merged posts for FE sheet")
    new_crawl_posts: list[dict] = Field(default_factory=list, description="Posts from this crawl only")
    intents: Optional[list] = Field(default=None, description="Intents từ IntentAgent (nếu có)")
    crawl_logs: list[str] = Field(default_factory=list, description="Trace log của crawl pipeline")
    costSummary: dict = Field(default_factory=dict)
    error: Optional[str] = None
class ThreadsCrawlRequest(BaseModel):
    """Request body cho POST /api/crawl/threads."""
    platform: str = Field(default="threads", description="Platform identifier")
    domain: str = Field(default="", description="Business domain / ngành hàng")
    keywords: list[str] = Field(..., min_length=1, description="Danh sách keywords cần crawl")
    # Apify config — override từ request, fallback sang .env
    apify_token: Optional[str] = Field(default=None, description="Apify API token")
    autocomplete_limit: int = Field(default=5, ge=1, le=20)
    search_limit: int = Field(default=2, ge=1, le=50)
    posts_limit: int = Field(default=2, ge=1, le=50)
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
    crawl_posts: list[dict] = Field(default_factory=list, description="All merged posts for FE sheet")
    new_crawl_posts: list[dict] = Field(default_factory=list, description="Posts from this crawl only")
    intents: Optional[list] = Field(default=None, description="Intents từ IntentAgent (nếu có)")
    crawl_logs: list[str] = Field(default_factory=list, description="Trace log của crawl pipeline")
    costSummary: dict = Field(default_factory=dict)
    error: Optional[str] = None

class TiktokCrawlRequest(BaseModel):
    """Request body cho POST /api/crawl/tiktok."""
    platform: str = Field(default="tiktok", description="Platform identifier")
    domain: str = Field(default="", description="Business domain / ngành hàng")
    keywords: list[str] = Field(..., min_length=1, description="Danh sách keywords cần crawl")
    apify_token: Optional[str] = Field(default=None, description="Apify API token")
    search_limit: int = Field(default=2, ge=1, le=50)
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
    crawl_posts: list[dict] = Field(default_factory=list, description="All merged posts for FE sheet")
    new_crawl_posts: list[dict] = Field(default_factory=list, description="Posts from this crawl only")
    intents: Optional[list] = Field(default=None, description="Intents từ IntentAgent (nếu có)")
    crawl_logs: list[str] = Field(default_factory=list, description="Trace log của crawl pipeline")
    costSummary: dict = Field(default_factory=dict)
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
        with cost_operation("crawl_facebook"):
            raw_content = await crawler.run(keywords=_normalize_keywords(req.keywords))
    except Exception as exc:
        logger.exception("Crawl failed")
        return FacebookCrawlResponse(
            success=False,
            platform=req.platform,
            keywords=req.keywords,
            raw_content_preview="",
            raw_content_length=0,
            raw_content="",
            costSummary=summarize_run(refresh_apify=True),
            error=f"Crawl error: {exc}",
        )
    # ---- Store crawled content: prepend to JSON file + sync pipeline state ----
    new_posts, all_posts = persist_crawl_posts(req.platform, raw_content)
    if req.extract_intents:
        with cost_operation("crawl_facebook"):
            intents, crawl_logs = await _mine_and_store(
                raw_content, req.domain, req.platform, _normalize_keywords(req.keywords)
            )
    else:
        intents, crawl_logs = [], _crawl_logs(
            req.platform, _normalize_keywords(req.keywords), len(new_posts), len(all_posts)
        )
    # ---- Response ----
    return FacebookCrawlResponse(
        success=True,
        platform=req.platform,
        keywords=req.keywords,
        raw_content_preview=raw_content[:500],
        raw_content_length=len(raw_content),
        raw_content=raw_content,
        crawl_posts=all_posts,
        new_crawl_posts=new_posts,
        intents=intents,
        crawl_logs=crawl_logs,
        costSummary=summarize_run(refresh_apify=True),
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
        with cost_operation("crawl_threads"):
            raw_content = await crawler.run(keywords=_normalize_keywords(req.keywords))
    except Exception as exc:
        logger.exception("Crawl failed")
        return ThreadsCrawlResponse(
            success=False,
            platform=req.platform,
            keywords=req.keywords,
            raw_content_preview="",
            raw_content_length=0,
            raw_content="",
            costSummary=summarize_run(refresh_apify=True),
            error=f"Crawl error: {exc}",
        )
    new_posts, all_posts = persist_crawl_posts(req.platform, raw_content)
    if req.extract_intents:
        with cost_operation("crawl_threads"):
            intents, crawl_logs = await _mine_and_store(
                raw_content, req.domain, req.platform, _normalize_keywords(req.keywords)
            )
    else:
        intents, crawl_logs = [], _crawl_logs(
            req.platform, _normalize_keywords(req.keywords), len(new_posts), len(all_posts)
        )
    return ThreadsCrawlResponse(
        success=True,
        platform=req.platform,
        keywords=req.keywords,
        raw_content_preview=raw_content[:500],
        raw_content_length=len(raw_content),
        raw_content=raw_content,
        crawl_posts=all_posts,
        new_crawl_posts=new_posts,
        intents=intents,
        crawl_logs=crawl_logs,
        costSummary=summarize_run(refresh_apify=True),
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
        with cost_operation("crawl_tiktok"):
            raw_content = await crawler.run(keywords=_normalize_keywords(req.keywords))
    except Exception as exc:
        logger.exception("Crawl failed")
        return TiktokCrawlResponse(
            success=False,
            platform=req.platform,
            keywords=req.keywords,
            raw_content_preview="",
            raw_content_length=0,
            raw_content="",
            costSummary=summarize_run(refresh_apify=True),
            error=f"Crawl error: {exc}",
        )
    
    new_posts, all_posts = persist_crawl_posts(req.platform, raw_content)
    if req.extract_intents:
        with cost_operation("crawl_tiktok"):
            intents, crawl_logs = await _mine_and_store(
                raw_content, req.domain, req.platform, _normalize_keywords(req.keywords), source_type="tiktok"
            )
    else:
        intents, crawl_logs = [], _crawl_logs(
            req.platform, _normalize_keywords(req.keywords), len(new_posts), len(all_posts)
        )
    return TiktokCrawlResponse(
        success=True,
        platform=req.platform,
        keywords=req.keywords,
        raw_content_preview=raw_content[:500],
        raw_content_length=len(raw_content),
        raw_content=raw_content,
        crawl_posts=all_posts,
        new_crawl_posts=new_posts,
        intents=intents,
        crawl_logs=crawl_logs,
        costSummary=summarize_run(refresh_apify=True),
    )

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@router.get("/posts")
async def get_crawl_posts():
    """Return all persisted crawl posts (newest batches at the top)."""
    posts = load_posts()
    return {"posts": posts, "count": len(posts)}


@router.post("/posts/reset")
async def reset_crawl_posts():
    """Clear persisted crawl sheet + in-memory social content."""
    clear_posts()
    get_state().raw_social_content = ""
    return {"success": True, "posts": [], "count": 0}


class DeletePostsRequest(BaseModel):
    """Indices (vào sheet hiện tại) của các post cần xóa."""
    indices: list[int] = Field(..., min_length=1, description="Vị trí post cần xóa khỏi sheet")


@router.post("/posts/delete")
async def delete_crawl_posts(req: DeletePostsRequest):
    """Remove selected posts (by index) from the persisted sheet + resync social content."""
    posts = load_posts()
    drop = {i for i in req.indices if 0 <= i < len(posts)}
    remaining = [p for i, p in enumerate(posts) if i not in drop]
    save_posts(remaining)
    sync_social_content_to_state()
    return {"success": True, "posts": remaining, "count": len(remaining)}


@router.get("/health")
async def crawl_health():
    """Kiểm tra crawl module hoạt động."""
    return {"status": "ok", "module": "crawl", "supported_platforms": ["facebook", "threads", "tiktok"]}
