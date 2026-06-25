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
from src.config import settings
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/crawl", tags=["crawl"])
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
    search_limit: int = Field(default=5, ge=1, le=50)
    posts_limit: int = Field(default=5, ge=1, le=50)
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
    error: Optional[str] = None
# ---------------------------------------------------------------------------
# Endpoint
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
    # ---- Optional: chạy IntentAgent ----
    intents = None
    try:
        # Import lazy để không crash nếu agent chưa sẵn sàng
        from src.agents.intent_agent import IntentAgent
        from src.models.state import AgentState, RawInput
        state = AgentState()
        state.raw_input = RawInput(content=raw_content, domain=req.domain)
        # Override LLM config nếu request có gửi
        agent_kwargs = {}
        if req.model:
            agent_kwargs["model"] = req.model
        if req.api_key:
            agent_kwargs["api_key"] = req.api_key
        agent = IntentAgent(**agent_kwargs) if agent_kwargs else IntentAgent()
        result_state = await agent.run(state)
        # Lấy intents từ state sau khi agent xử lý
        if hasattr(result_state, "intents"):
            intents = result_state.intents
        elif hasattr(result_state, "intent_output"):
            intents = result_state.intent_output
    except ImportError:
        logger.warning("IntentAgent not available — returning raw content only.")
    except Exception as exc:
        logger.warning("IntentAgent failed: %s — returning raw content only.", exc)
    # ---- Response ----
    return FacebookCrawlResponse(
        success=True,
        platform=req.platform,
        keywords=req.keywords,
        raw_content_preview=raw_content[:500],
        raw_content_length=len(raw_content),
        raw_content=raw_content,
        intents=intents,
    )
# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@router.get("/health")
async def crawl_health():
    """Kiểm tra crawl module hoạt động."""
    return {"status": "ok", "module": "crawl", "supported_platforms": ["facebook"]}
