import json

from openai import AsyncOpenAI
from pydantic import BaseModel

from src.llm.base import LLMClient


class OpenAIClient(LLMClient):
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        response = await self.client.chat.completions.create(
            model=self.model, messages=messages
        )
        return response.choices[0].message.content

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
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            raw = raw.rsplit("```", 1)[0]
        data = json.loads(raw.strip())
        return schema.model_validate(data)
