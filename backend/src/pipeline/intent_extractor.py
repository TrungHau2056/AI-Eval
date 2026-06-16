import json
import logging

from src.chunking.text_chunker import chunk_text
from src.llm.base import LLMClient
from src.models.schemas import Intent, RawInput
from src.prompts.templates import INTENT_SYSTEM_PROMPT, INTENT_USER_PROMPT

logger = logging.getLogger(__name__)


class IntentExtractor:
    def __init__(self, llm: LLMClient, max_chunk_tokens: int = 50000):
        self.llm = llm
        self.max_chunk_tokens = max_chunk_tokens

    async def extract(self, raw_input: RawInput, guidance: str = "") -> list[Intent]:
        chunks = chunk_text(raw_input.content, max_tokens=self.max_chunk_tokens)
        all_intents: list[Intent] = []

        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i + 1}/{len(chunks)}")
            prompt = INTENT_USER_PROMPT.format(raw_text=chunk)
            if guidance:
                prompt += f"\n\nHướng dẫn thêm từ người dùng: {guidance}"
            raw = await self.llm.generate(prompt, system_prompt=INTENT_SYSTEM_PROMPT)
            intents = self._parse_response(raw)
            all_intents.extend(intents)

        return self._deduplicate(all_intents)

    async def regenerate(
        self, existing: list[Intent], raw_input: RawInput, guidance: str = ""
    ) -> list[Intent]:
        new_intents = await self.extract(raw_input, guidance)
        existing_contexts = {(i.context, i.goal) for i in existing}
        fresh = [
            ni for ni in new_intents if (ni.context, ni.goal) not in existing_contexts
        ]
        return existing + fresh

    def _parse_response(self, raw: str) -> list[Intent]:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]
        try:
            data = json.loads(text.strip())
        except json.JSONDecodeError:
            logger.error("Failed to parse LLM response as JSON")
            return []
        items = data.get("intents", data if isinstance(data, list) else [])
        return [
            Intent(
                context=item.get("context", ""),
                goal=item.get("goal", ""),
                evidence=item.get("evidence", []),
            )
            for item in items
            if item.get("context") and item.get("goal")
        ]

    def _deduplicate(self, intents: list[Intent]) -> list[Intent]:
        seen: set[tuple[str, str]] = set()
        result: list[Intent] = []
        for intent in intents:
            key = (intent.context.strip().lower(), intent.goal.strip().lower())
            if key not in seen:
                seen.add(key)
                result.append(intent)
        return result
