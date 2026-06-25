"""
Test script cho Facebook Crawl Pipeline.
Chạy: python test_crawl.py
Yêu cầu: pip install httpx

Bao gồm End-to-End Pipeline: Autocomplete -> Search -> Scrape -> Clean Data
"""

import asyncio
import httpx
import json

# ============================================================
# CONFIG
# ============================================================
APIFY_TOKEN = ""
APIFY_BASE  = "https://api.apify.com"
TIMEOUT     = 600.0

AUTOCOMPLETE_ACTOR = "automation-lab~google-autocomplete-scraper"
SEARCH_ACTOR       = "scraper_one~facebook-posts-search"
POSTS_ACTOR        = "apify~facebook-posts-scraper"


# ============================================================
# HELPER — chạy 1 actor Apify
# ============================================================
async def run_actor(client: httpx.AsyncClient, actor_id: str, run_input: dict) -> list[dict]:
    """Start actor → wait → get items."""
    params = {"token": APIFY_TOKEN}

    print(f"\n  ▶ Starting {actor_id} ...")
    resp = await client.post(
        f"{APIFY_BASE}/v2/acts/{actor_id}/runs",
        params=params,
        json=run_input,
        headers={"Content-Type": "application/json"},
    )
    if resp.status_code != 201:
        print(f"  ✗ Start failed: {resp.status_code}")
        return []
    
    run_data = resp.json()["data"]
    run_id = run_data["id"]
    dataset_id = run_data["defaultDatasetId"]
    print(f"  ✓ Started — run_id={run_id}")

    print(f"  ⏳ Waiting for finish (max 5 min) ...")
    resp = await client.get(
        f"{APIFY_BASE}/v2/actor-runs/{run_id}",
        params={**params, "waitForFinish": "300"},
    )
    resp.raise_for_status()
    status = resp.json()["data"]["status"]
    
    if status != "SUCCEEDED":
        print(f"  ✗ Actor finished with status: {status}")
        return []

    resp = await client.get(
        f"{APIFY_BASE}/v2/datasets/{dataset_id}/items",
        params=params,
    )
    resp.raise_for_status()
    items = resp.json()
    print(f"  ✓ Got {len(items)} items from {actor_id}")
    return items


# ============================================================
# DATA PROCESSOR
# ============================================================
def clean_scraped_data(raw_items: list[dict]) -> list[dict]:
    """
    Xử lý JSON thô từ apify~facebook-posts-scraper
    Giữ lại đúng 3 trường: link, liked, content
    """
    cleaned_data = []
    
    for item in raw_items:
        if "error" in item:
            continue
            
        url = item.get("url") or item.get("facebookUrl") or ""
        content = item.get("text") or item.get("postText") or item.get("message") or ""
        liked = item.get("reactionLikeCount") or item.get("likesCount") or item.get("topReactionsCount") or 0
        
        # Chỉ giữ lại bài viết thực sự có nội dung
        if url and content:
            cleaned_data.append({
                "link": url,
                "liked": liked,
                "content": content.strip()
            })
            
    return cleaned_data


# ============================================================
# FULL PIPELINE (End-to-End Test)
# ============================================================
async def test_full_pipeline(seed_keyword: str = "quán cà phê Hà Nội"):
    print("=" * 60)
    print(f"PIPELINE START: '{seed_keyword}'")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # 1. Autocomplete
        ac_input = {
            "keywords": [seed_keyword],
            "language": "vi",
            "country": "vn",
            "maxDepth": 1,
            "maxSuggestionsPerKeyword": 3,
            "appendAlphabet": False,
        }
        ac_items = await run_actor(client, AUTOCOMPLETE_ACTOR, ac_input)
        queries = [i.get("suggestion") for i in ac_items if i.get("suggestion")]
        if not queries:
            queries = [seed_keyword]
        print(f"  ➜ Queries for search: {queries}")

        # 2. Search Posts (chỉ search query đầu tiên để test nhanh)
        query = queries[0]
        search_input = {
            "query": query,
            "resultsCount": 10,
            "searchType": "top",
        }
        search_items = await run_actor(client, SEARCH_ACTOR, search_input)
        
        urls = []
        for item in search_items:
            url = item.get("url") or item.get("post_url")
            if url and url not in urls:
                urls.append(url)
        print(f"  ➜ URLs found: {len(urls)}")

        # 3. Scrape Deep Posts (chỉ scrape 3 URL đầu để test nhanh)
        if not urls:
            print("  ✗ No URLs found to scrape.")
            return

        scrape_input = {
            "startUrls": [{"url": u} for u in urls[:3]],
            "resultsLimit": 3,
        }
        raw_scraped_items = await run_actor(client, POSTS_ACTOR, scrape_input)

        # 4. Cleanup Data
        print("\n" + "=" * 60)
        print("FINAL PROCESSED DATA (link, liked, content)")
        print("=" * 60)
        
        final_json = clean_scraped_data(raw_scraped_items)
        print(json.dumps(final_json, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
