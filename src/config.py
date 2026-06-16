from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str = ""
    openai_api_key: str = ""
    default_model: str = "gemini"
    chunk_max_tokens: int = 50000
    chunk_overlap_tokens: int = 500

    model_config = {"env_file": ".env", "env_prefix": ""}


settings = Settings()
