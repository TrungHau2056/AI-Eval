"""
BaseCrawler — abstract base class for all platform crawlers.
Cung cấp:
- _run_actor(): gọi Apify actor qua REST API (start → wait → get items)
- run(): abstract method mỗi platform tự implement
"""
from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from typing import Any
import httpx
logger = logging.getLogger(__name__)
# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
APIFY_BASE_URL = "https://api.apify.com"
DEFAULT_WAIT_SECS = 300          # tối đa chờ actor chạy xong
HTTP_TIMEOUT = 600.0             # httpx timeout tổng (bao gồm cả wait)
class BaseCrawler(ABC):
    """Abstract base cho mọi platform crawler (Facebook, TikTok, YouTube …)."""
    def __init__(self, apify_token: str) -> None:
        if not apify_token:
            raise ValueError("apify_token is required — pass via request body or APIFY_TOKEN env.")
        self.token = apify_token
        self.base_url = APIFY_BASE_URL
    # ------------------------------------------------------------------
    # Apify actor runner (dùng chung cho mọi crawler)
    # ------------------------------------------------------------------
    async def _run_actor(
        self,
        actor_id: str,
        run_input: dict[str, Any],
        wait_secs: int = DEFAULT_WAIT_SECS,
    ) -> list[dict[str, Any]]:
        """
        Chạy 1 Apify actor và trả về list dataset items.
        Flow:
            1. POST  /v2/acts/{actor_id}/runs          → start run
            2. GET   /v2/actor-runs/{run_id}?waitForFinish  → đợi xong
            3. GET   /v2/datasets/{dataset_id}/items    → lấy kết quả
        """
        headers = {"Content-Type": "application/json"}
        params_auth = {"token": self.token}
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            # ---- 1. Start the actor run ----
            start_url = f"{self.base_url}/v2/acts/{actor_id}/runs"
            logger.info("Starting actor %s …", actor_id)
            resp = await client.post(
                start_url,
                params=params_auth,
                json=run_input,
                headers=headers,
            )
            resp.raise_for_status()
            run_data: dict = resp.json().get("data", {})
            run_id: str = run_data["id"]
            dataset_id: str = run_data["defaultDatasetId"]
            logger.info("Actor %s started — run_id=%s, dataset=%s", actor_id, run_id, dataset_id)
            # ---- 2. Wait for the run to finish ----
            wait_url = f"{self.base_url}/v2/actor-runs/{run_id}"
            wait_params = {**params_auth, "waitForFinish": str(wait_secs)}
            resp = await client.get(wait_url, params=wait_params)
            resp.raise_for_status()
            status = resp.json().get("data", {}).get("status", "UNKNOWN")
            logger.info("Actor %s finished — status=%s", actor_id, status)
            if status not in ("SUCCEEDED",):
                logger.warning("Actor %s ended with status=%s — returning empty list.", actor_id, status)
                return []
            # ---- 3. Fetch dataset items ----
            items_url = f"{self.base_url}/v2/datasets/{dataset_id}/items"
            resp = await client.get(items_url, params=params_auth)
            resp.raise_for_status()
            items: list[dict] = resp.json()
            logger.info("Actor %s returned %d items.", actor_id, len(items))
            return items
    # ------------------------------------------------------------------
    # Abstract entry-point — mỗi subclass tự implement
    # ------------------------------------------------------------------
    @abstractmethod
    async def run(self, keywords: list[str]) -> str:
        """
        Chạy full pipeline crawl và trả về 1 string nội dung thô
        (sẵn sàng đẩy vào IntentAgent.run() làm RawInput.content).
        """
        ...
