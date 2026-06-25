from pydantic_settings import BaseSettings


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

    model_config = {"env_file": ".env", "env_prefix": ""}


settings = Settings()
