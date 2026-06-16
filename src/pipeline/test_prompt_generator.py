import json
import logging

from src.llm.base import LLMClient
from src.models.schemas import Intent, Persona, TestCasePrompt
from src.prompts.templates import TEST_PROMPT_SYSTEM_PROMPT, TEST_PROMPT_USER_PROMPT

logger = logging.getLogger(__name__)


class TestCasePromptGenerator:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def generate(
        self, intents: list[Intent], personas: list[Persona], guidance: str = ""
    ) -> list[TestCasePrompt]:
        intent_map = {i.id: i for i in intents}
        all_prompts: list[TestCasePrompt] = []
        for persona in personas:
            intent = intent_map.get(persona.intent_id)
            if not intent:
                continue
            logger.info(f"Generating test prompt for persona: {persona.name}")
            prompt = TEST_PROMPT_USER_PROMPT.format(
                context=intent.context,
                goal=intent.goal,
                persona_name=persona.name,
                persona_description=persona.description,
                trait_type=persona.trait_type,
                guidance=f"\nHướng dẫn thêm: {guidance}" if guidance else "",
            )
            raw = await self.llm.generate(
                prompt, system_prompt=TEST_PROMPT_SYSTEM_PROMPT
            )
            test_prompt = self._parse_response(raw, persona.id, intent.id)
            if test_prompt:
                all_prompts.append(test_prompt)
        return all_prompts

    async def regenerate_for_persona(
        self, intent: Intent, persona: Persona, guidance: str = ""
    ) -> TestCasePrompt | None:
        prompt = TEST_PROMPT_USER_PROMPT.format(
            context=intent.context,
            goal=intent.goal,
            persona_name=persona.name,
            persona_description=persona.description,
            trait_type=persona.trait_type,
            guidance=f"\nHướng dẫn thêm: {guidance}" if guidance else "",
        )
        raw = await self.llm.generate(prompt, system_prompt=TEST_PROMPT_SYSTEM_PROMPT)
        return self._parse_response(raw, persona.id, intent.id)

    def _parse_response(
        self, raw: str, persona_id: str, intent_id: str
    ) -> TestCasePrompt | None:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]
        try:
            data = json.loads(text.strip())
        except json.JSONDecodeError:
            logger.error("Failed to parse LLM response as JSON")
            return None
        prompt_text = data.get("prompt_text", "")
        if not prompt_text:
            return None
        return TestCasePrompt(
            persona_id=persona_id,
            intent_id=intent_id,
            prompt_text=prompt_text,
        )
