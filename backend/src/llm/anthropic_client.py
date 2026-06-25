"""
Anthropic Claude Client
========================
Dùng anthropic SDK. Model mặc định: claude-sonnet-4-6.
"""
import json
import anthropic
from pydantic import BaseModel

from src.llm.base import LLMClient


class AnthropicClient(LLMClient):
    """
    Client cho Anthropic API (claude-sonnet-4-6, claude-opus-*...).

    Usage:
        client = AnthropicClient(api_key="sk-ant-...")
        text = await client.generate("Tell me about Vietnam")
    """

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        kwargs: dict = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = await self.client.messages.create(**kwargs)
        return response.content[0].text

    async def generate_structured(
        self, prompt: str, schema: type[BaseModel], system_prompt: str = ""
    ) -> BaseModel:
        schema_json = schema.model_json_schema()
        json_instruction = (
            f"\n\nRespond ONLY with valid JSON matching this schema:\n"
            f"{json.dumps(schema_json, indent=2, ensure_ascii=False)}\n"
            f"Do NOT include markdown code fences or any text outside the JSON."
        )
        full_prompt = prompt + json_instruction
        raw = await self.generate(full_prompt, system_prompt)
        raw = _strip_code_fences(raw)
        data = json.loads(raw)
        return schema.model_validate(data)


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0]
    return text.strip()
