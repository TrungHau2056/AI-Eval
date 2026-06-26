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
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from src.crawlers.facebook_crawler import FacebookCrawler
from src.crawlers.threads_crawler import ThreadsCrawler
from src.crawlers.tiktok_crawler import TiktokCrawler
from src.config import settings
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
class FacebookCrawlResponse(BaseModel):
    """Response cho crawl endpoint."""
    success: bool
    platform: str
    keywords: list[str]
    raw_content_preview: str = Field(description="Preview 500 ký tự đầu của raw content")
    raw_content_length: int = Field(description="Tổng số ký tự raw content")
    raw_content: str = Field(description="Toàn bộ raw content đã crawl")
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

class ThreadsCrawlResponse(BaseModel):
    """Response cho crawl endpoint."""
    success: bool
    platform: str
    keywords: list[str]
    raw_content_preview: str = Field(description="Preview 500 ký tự đầu của raw content")
    raw_content_length: int = Field(description="Tổng số ký tự raw content")
    raw_content: str = Field(description="Toàn bộ raw content đã crawl")
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

class TiktokCrawlResponse(BaseModel):
    """Response cho tiktok crawl endpoint."""
    success: bool
    platform: str
    keywords: list[str]
    raw_content_preview: str = Field(description="Preview 500 ký tự đầu của raw content")
    raw_content_length: int = Field(description="Tổng số ký tự raw content")
    raw_content: str = Field(description="Toàn bộ raw content đã crawl")
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
    # ---- Mine intents + persist to pipeline state ----
    intents, crawl_logs = await _mine_and_store(
        raw_content, req.domain, req.platform, req.keywords
    )
    # ---- Response ----
    return FacebookCrawlResponse(
        success=True,
        platform=req.platform,
        keywords=req.keywords,
        raw_content_preview=raw_content[:500],
        raw_content_length=len(raw_content),
        raw_content=raw_content,
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
    # ---- Mine intents + persist to pipeline state ----
    intents, crawl_logs = await _mine_and_store(
        raw_content, req.domain, req.platform, req.keywords
    )
    # ---- Response ----
    return ThreadsCrawlResponse(
        success=True,
        platform=req.platform,
        keywords=req.keywords,
        raw_content_preview=raw_content[:500],
        raw_content_length=len(raw_content),
        raw_content=raw_content,
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
    
    # ---- Mine intents + persist to pipeline state ----
    intents, crawl_logs = await _mine_and_store(
        raw_content, req.domain, req.platform, req.keywords, source_type="tiktok"
    )
    return TiktokCrawlResponse(
        success=True,
        platform=req.platform,
        keywords=req.keywords,
        raw_content_preview=raw_content[:500],
        raw_content_length=len(raw_content),
        raw_content=raw_content,
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
