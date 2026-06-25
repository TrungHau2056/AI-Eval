"""
Crawlers package — platform-specific data crawlers powered by Apify.
Usage:
    from src.crawlers import FacebookCrawler
    crawler = FacebookCrawler(apify_token="apify_api_xxx")
    content = await crawler.run(keywords=["từ khóa 1", "từ khóa 2"])
"""
from src.crawlers.base import BaseCrawler
from src.crawlers.facebook_crawler import FacebookCrawler
__all__ = ["BaseCrawler", "FacebookCrawler"]
