import os
from pydantic_settings import BaseSettings

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BACKEND_DIR, ".env")

class Settings(BaseSettings):
    gemini_api_key: str = ""
    openai_api_key: str = ""
    default_model: str = "gemini"
    chunk_max_tokens: int = 50000
    chunk_overlap_tokens: int = 500
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_base_url: str = "https://cloud.langfuse.com"
    langfuse_capture_io: bool = False

    # LLM model ids (cấu hình được qua .env)
    gemini_model: str = "gemini-2.5-flash"

    # Gap analysis / IntentComparator
    embedding_model: str = "models/gemini-embedding-001"
    match_high: float = 0.85  # sim >= high → auto match
    match_low: float = 0.55  # sim <= low → auto khác; ở giữa → LLM chấm

    # Apify (social-media crawl)
    apify_token: str = ""

    model_config = {"env_file": ENV_PATH, "env_prefix": ""}


settings = Settings()
