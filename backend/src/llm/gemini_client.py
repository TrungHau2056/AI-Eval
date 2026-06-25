import json

import google.generativeai as genai
from pydantic import BaseModel

from src.llm.base import LLMClient


class GeminiClient(LLMClient):
    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [system_prompt]})
            contents.append({"role": "model", "parts": ["Understood."]})
        contents.append({"role": "user", "parts": [prompt]})
        response = await self.model.generate_content_async(contents)
        return response.text

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
