"""
LLM Clients cho Persona Agent
==============================
Tách riêng khỏi src/llm/ của team chính để:
  1. Không conflict nếu team chính thay đổi interface
  2. Thêm Anthropic + OpenRouter mà không phá vỡ gemini/openai của team
  3. Persona agent có thể dùng model khác (claude-3-5-sonnet vs gpt-4o)

Nếu muốn unify sau này:
  - Anthropic/OpenRouter client có thể extract ra src/llm/ chung
  - Chỉ cần đảm bảo cùng interface abstract generate() / generate_structured()
"""
from abc import ABC, abstractmethod
from pydantic import BaseModel


class PersonaAgentLLMBase(ABC):
    """
    Interface LLM cho persona agent.
    Giữ cùng signature với LLMClient của team chính (src/llm/base.py)
    để dễ swap/integrate sau này.
    """

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Sinh text tự do."""
        ...

    @abstractmethod
    async def generate_structured(
        self, prompt: str, schema: type[BaseModel], system_prompt: str = ""
    ) -> BaseModel:
        """Sinh JSON và parse thành Pydantic model."""
        ...
