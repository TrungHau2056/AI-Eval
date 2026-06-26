import asyncio
import os
import sys
import logging

from dotenv import load_dotenv

backend_path = os.path.abspath(os.path.dirname(__file__))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from src.crawlers.facebook_crawler import FacebookCrawler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

load_dotenv(os.path.join(backend_path, ".env"))


async def main():
    token = os.environ.get("APIFY_TOKEN", "")
    if not token:
        print("Missing APIFY_TOKEN in backend/.env")
        return

    crawler = FacebookCrawler(
        apify_token=token,
        search_limit=10,
        posts_limit=3,
    )

    keywords = ["quán cà phê Hà Nội"]
    print(f"Starting crawl Facebook for keyword: {keywords}")

    try:
        result = await crawler.run(keywords)

        output_path = os.path.join(backend_path, "facebook_crawl_output.txt")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result)

        print(f"DONE! Result saved to: {output_path}")
    except Exception as e:
        print(f"Error during crawl: {e}")


if __name__ == "__main__":
    asyncio.run(main())
