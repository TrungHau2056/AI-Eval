import asyncio
import os
import sys
import logging
from dotenv import load_dotenv
import sys
import logging

# Thêm thư mục backend vào sys.path
backend_path = os.path.abspath(os.path.dirname(__file__))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from src.crawlers.threads_crawler import ThreadsCrawler
from src.config import settings

# Hiển thị log ra console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Load backend/.env
load_dotenv(os.path.join(backend_path, ".env"))

async def main():
    token = os.environ.get("APIFY_TOKEN", "")
    if not token:
        print("Missing APIFY_TOKEN")
        return
        
    crawler = ThreadsCrawler(
        apify_token=token,
        autocomplete_limit=1,
        search_limit=2,
        posts_limit=2
    )
    
    keywords = ["Vinfast VF8"]
    print(f"Starting crawl Threads for keyword: {keywords}")
    
    try:
        result = await crawler.run(keywords)
        
        # Đường dẫn file output
        output_path = os.path.join(os.path.dirname(__file__), "threads_crawl_output.txt")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result)
            
        print(f"DONE! Result saved to: {output_path}")
    except Exception as e:
        print(f"Error during crawl: {e}")

if __name__ == "__main__":
    asyncio.run(main())
