"""
LLM Factory cho Persona Agent
===============================
create_persona_llm(provider, api_key, model?) → PersonaAgentLLMBase
"""
from .base import PersonaAgentLLMBase
from .anthropic_client import AnthropicClient
from .openrouter_client import OpenRouterClient


def create_persona_llm(
    provider: str,
    api_key: str,
    model: str = "",
) -> PersonaAgentLLMBase:
    """
    Factory tạo LLM client cho persona agent.

    Args:
        provider: "anthropic" hoặc "openrouter"
        api_key:  API key tương ứng
        model:    Override model string nếu muốn (để trống = dùng default)

    Returns:
        PersonaAgentLLMBase instance

    Raises:
        ValueError: provider không hợp lệ
    """
    if provider == "anthropic":
        kwargs = {}
        if model:
            kwargs["model"] = model
        return AnthropicClient(api_key=api_key, **kwargs)

    if provider == "openrouter":
        kwargs = {}
        if model:
            kwargs["model"] = model
        return OpenRouterClient(api_key=api_key, **kwargs)

    raise ValueError(
        f"Unsupported provider: '{provider}'. "
        f"Choose 'anthropic' or 'openrouter'."
    )
