"""
End-to-end test for FacebookCrawler (search → scrape).
Uses the same FacebookCrawler class and actors as production.

Chạy:
    cd backend
    python tests/test_facebook_crawler.py
"""

import asyncio
import json
import logging
import os
import sys

from dotenv import load_dotenv

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

load_dotenv(os.path.join(BACKEND_DIR, ".env"))

from src.crawlers.facebook_crawler import FacebookCrawler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def test_full_pipeline(seed_keyword: str = "quán cà phê Hà Nội") -> None:
    token = os.getenv("APIFY_TOKEN", "")
    if not token:
        raise SystemExit("Set APIFY_TOKEN in backend/.env")

    print("=" * 60)
    print(f"PIPELINE START: '{seed_keyword}'")
    print("=" * 60)

    crawler = FacebookCrawler(
        apify_token=token,
        search_limit=10,
        posts_limit=3,
    )
    result = await crawler.run([seed_keyword])

    print("\n" + "=" * 60)
    print("FINAL OUTPUT")
    print("=" * 60)

    parsed = json.loads(result)
    print(json.dumps(parsed, indent=2, ensure_ascii=False))
    print(f"\n✓ {len(parsed)} post(s)")


if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
