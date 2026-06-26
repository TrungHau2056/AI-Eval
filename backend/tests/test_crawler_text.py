import json

from src.crawlers.facebook_crawler import FacebookCrawler


def test_facebook_extract_text_handles_nested_dict_message():
    post = {
        "url": "https://www.facebook.com/groups/demo/posts/1/",
        "message": {"text": "Nested caption from Apify actor"},
        "user": {"name": "Demo User"},
        "reactions": {"like": 3},
        "comments": 1,
    }
    assert FacebookCrawler._extract_text(post) == "Nested caption from Apify actor"


def test_facebook_format_output_handles_nested_text_fields():
    posts = [
        {
            "url": "https://www.facebook.com/groups/demo/posts/1/",
            "text": {"text": "Hello from nested text field"},
            "user": "author_a",
            "likeCount": 5,
            "commentsCount": 2,
        }
    ]
    parsed = json.loads(FacebookCrawler("fake_token")._format_output(posts))
    assert len(parsed) == 1
    assert parsed[0]["captionText"] == "Hello from nested text field"
