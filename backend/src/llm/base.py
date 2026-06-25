from abc import ABC, abstractmethod

from pydantic import BaseModel


class LLMClient(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str = "") -> str: ...

    @abstractmethod
    async def generate_structured(
        self, prompt: str, schema: type[BaseModel], system_prompt: str = ""
    ) -> BaseModel: ...
