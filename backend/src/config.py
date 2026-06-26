import os
from pydantic_settings import BaseSettings

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../backend
ROOT_DIR = os.path.dirname(BACKEND_DIR)                                     # repo root
# Root .env is the documented location (README: `cp .env.example .env`);
# backend/.env (if present) overrides it. Missing files are ignored.
ENV_FILES = (os.path.join(ROOT_DIR, ".env"), os.path.join(BACKEND_DIR, ".env"))

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

    model_config = {"env_file": ENV_FILES, "env_prefix": ""}


settings = Settings()
