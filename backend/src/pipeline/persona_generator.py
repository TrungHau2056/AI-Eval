import json
import logging

from src.llm.base import LLMClient
from src.models.schemas import Intent, Persona
from src.prompts.templates import PERSONA_SYSTEM_PROMPT, PERSONA_USER_PROMPT

logger = logging.getLogger(__name__)


class PersonaGenerator:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def generate(
        self, intents: list[Intent], guidance: str = ""
    ) -> list[Persona]:
        all_personas: list[Persona] = []
        for intent in intents:
            logger.info(f"Generating personas for intent: {intent.goal}")
            prompt = PERSONA_USER_PROMPT.format(
                context=intent.context,
                goal=intent.goal,
                evidence=", ".join(intent.evidence) if intent.evidence else "N/A",
                guidance=f"\nHướng dẫn thêm: {guidance}" if guidance else "",
            )
            raw = await self.llm.generate(prompt, system_prompt=PERSONA_SYSTEM_PROMPT)
            personas = self._parse_response(raw, intent.id)
            all_personas.extend(personas)
        return all_personas

    async def regenerate_for_intent(
        self, intent: Intent, guidance: str = ""
    ) -> list[Persona]:
        prompt = PERSONA_USER_PROMPT.format(
            context=intent.context,
            goal=intent.goal,
            evidence=", ".join(intent.evidence) if intent.evidence else "N/A",
            guidance=f"\nHướng dẫn thêm: {guidance}" if guidance else "",
        )
        raw = await self.llm.generate(prompt, system_prompt=PERSONA_SYSTEM_PROMPT)
        return self._parse_response(raw, intent.id)

    def _parse_response(self, raw: str, intent_id: str) -> list[Persona]:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]
        try:
            data = json.loads(text.strip())
        except json.JSONDecodeError:
            logger.error("Failed to parse LLM response as JSON")
            return []
        items = data.get("personas", data if isinstance(data, list) else [])
        return [
            Persona(
                intent_id=intent_id,
                name=item.get("name", ""),
                description=item.get("description", ""),
                trait_type=item.get("trait_type", "easy"),
            )
            for item in items
            if item.get("name") and item.get("description")
        ]
