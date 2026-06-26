import pytest
from unittest.mock import AsyncMock
from src.crawlers.threads_crawler import ThreadsCrawler

@pytest.mark.asyncio
async def test_threads_crawler_pipeline_and_formatting():
    # Khởi tạo ThreadsCrawler với token ảo
    crawler = ThreadsCrawler(apify_token="fake_token")

    # Giả mạo (Mock) các cuộc gọi API thực tế
    crawler.get_autocomplete = AsyncMock(return_value=["iphone 15 tips", "iphone 15 reviews"])
    
    # Mock search_posts trả về các bài đăng thô từ Threads
    crawler.search_posts = AsyncMock(return_value=[
        {
            "url": "https://www.threads.net/@user_a/post/123",
            "text": "Check out this new iPhone 15!",
            "author": "user_a",
            "replies": [{"text": "Looks great!"}, {"text": "Agreed!"}]
        }
    ])

    # Mock scrape_posts trả về bài đăng cào sâu
    crawler.scrape_posts = AsyncMock(return_value=[
        {
            "url": "https://www.threads.net/@user_a/post/123",
            "text": "Check out this new iPhone 15! Detailed review here...",
            "author": "user_a",
            "replies": [{"text": "Looks great!"}, {"text": "Agreed!"}, {"text": "Nice review!"}]
        }
    ])

    # Chạy pipeline
    result = await crawler.run(["iphone 15"])

    # Kiểm tra kết quả định dạng đúng
    assert "[THREADS CRAWL]" in result
    assert "[THREADS POST] https://www.threads.net/@user_a/post/123" in result
    assert "Author: user_a" in result
    assert "Check out this new iPhone 15! Detailed review here..." in result
    assert "[REPLIES] (3 replies)" in result
    assert "  • Looks great!" in result
    assert "  • Nice review!" in result
