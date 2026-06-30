from src.config import settings
from src.llm.base import LLMClient
from src.llm.gemini_client import GeminiClient
from src.llm.openai_client import OpenAIClient


def create_llm_client(model: str, api_key: str) -> LLMClient:
    if model == "gemini":
        return GeminiClient(api_key, settings.gemini_model)
    if model == "openai":
        return OpenAIClient(api_key, settings.openai_model)
    raise ValueError(f"Unsupported model: {model}. Choose 'gemini' or 'openai'.")
