"""
OpenRouter Client
==================
OpenRouter dùng OpenAI-compatible API.
Hỗ trợ 100+ models (Claude, GPT-4o, Llama, Mistral...) qua 1 API key.

Default model: anthropic/claude-sonnet-4-6 (qua OpenRouter)
Có thể đổi sang: openai/gpt-4o, meta-llama/llama-3.3-70b-instruct, v.v.

Docs: https://openrouter.ai/docs
"""
import json
from openai import AsyncOpenAI
from pydantic import BaseModel

from src.llm.base import LLMClient


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterClient(LLMClient):
    """
    Client cho OpenRouter — wrapper trên OpenAI SDK, đổi base_url.

    Usage:
        client = OpenRouterClient(api_key="sk-or-v1-...")
        # Hoặc chỉ định model cụ thể:
        client = OpenRouterClient(api_key="...", model="openai/gpt-4o")
    """

    def __init__(
        self,
        api_key: str,
        model: str = "anthropic/claude-sonnet-4-6",
        site_url: str = "",
        site_name: str = "AI Test Case Generator",
    ):
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
            default_headers={
                "HTTP-Referer": site_url,
                "X-Title": site_name,
            },
        )
        self.model = model

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=4096,
        )
        return response.choices[0].message.content or ""

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
