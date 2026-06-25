import asyncio
import os
import sys
import logging
from dotenv import load_dotenv

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from src.crawlers.tiktok_crawler import TiktokCrawler

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

async def main():
    load_dotenv()
    token = os.getenv("APIFY_TOKEN")
    if not token:
        print("Missing APIFY_TOKEN in .env")
        return

    crawler = TiktokCrawler(
        apify_token=token,
        search_limit=2
    )

    keyword = "Vinfast VF8"
    print(f"Starting crawl TikTok for keyword: ['{keyword}']")
    
    result = await crawler.run(keywords=[keyword])
    
    output_file = "tiktok_crawl_output.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(result)
        
    print(f"DONE! Result saved to: {os.path.abspath(output_file)}")

if __name__ == "__main__":
    asyncio.run(main())
