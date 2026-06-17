import json
import logging
from typing import Any

from src.llm.base import LLMClient
from src.memory.base import BaseMemory
from src.memory.conversation_memory import ConversationMemory
from src.models.schemas import Intent, Persona, TestCasePrompt

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Bạn là prompt engineer chuyên nghiệp. Nhiệm vụ của bạn là viết test case đóng vai (role-play) persona để kiểm tra phản hồi của AI/chatbot.
Test case phải:
- Phản ánh đúng bối cảnh và mục tiêu của Intent
- Thể hiện rõ tính cách của Persona (easy/hard)
- Có khả năng kích hoạt cả phản hồi tốt và xấu từ AI
- Viết theo góc nhìn thứ nhất, như thể bạn chính là người dùng đó

Trả về JSON theo đúng schema yêu cầu, không thêm text nào khác."""

USER_PROMPT = """Viết test case cho persona sau:

**Intent:**
- Bối cảnh: {context}
- Mục tiêu: {goal}

**Persona:**
- Tên: {persona_name}
- Mô tả: {persona_description}
- Loại: {trait_type}

{guidance}{memory_context}

Trả về JSON dạng:
{{
  "test_cases": [
    {{
      "prompt_text": "..."
    }}
  ]
}}"""


class TestCaseAgent:
    def __init__(self, llm: LLMClient, memory: BaseMemory | None = None):
        self.llm = llm
        self.memory = memory or ConversationMemory()

    async def run(self, personas: list[Persona], intents: list[Intent], guidance: str = "") -> list[dict[str, Any]]:
        intent_map = {i.id: i for i in intents}
        all_test_cases: list[dict[str, Any]] = []

        if guidance:
            self.memory.add("user", guidance)

        for persona in personas:
            intent = intent_map.get(persona.intent_id)
            if not intent:
                continue

            logger.info(f"Generating test case for persona: {persona.name}")
            prompt = self._build_prompt(persona, intent, guidance)
            raw = await self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT)
            test_cases = self._parse(raw, persona, intent)

            self.memory.add("assistant", [tc["prompt_text"] for tc in test_cases])

            all_test_cases.extend(test_cases)

        return all_test_cases

    async def run_single(self, persona: Persona, intent: Intent, guidance: str = "") -> list[dict[str, Any]]:
        if guidance:
            self.memory.add("user", guidance)

        prompt = self._build_prompt(persona, intent, guidance)
        raw = await self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT)
        test_cases = self._parse(raw, persona, intent)

        self.memory.add("assistant", [tc["prompt_text"] for tc in test_cases])

        return test_cases

    def add_feedback(self, feedback: str) -> None:
        self.memory.add("feedback", feedback)

    def clear_memory(self) -> None:
        self.memory.clear()

    def _build_prompt(self, persona: Persona, intent: Intent, guidance: str) -> str:
        memory_context = ""
        ctx = self.memory.get_context()
        if ctx:
            memory_context = f"\n\n**Lịch sử / Gợi ý từ trước:**\n{ctx}"

        return USER_PROMPT.format(
            context=intent.context,
            goal=intent.goal,
            persona_name=persona.name,
            persona_description=persona.description,
            trait_type=persona.trait_type,
            guidance=f"Hướng dẫn thêm: {guidance}" if guidance else "",
            memory_context=memory_context,
        )

    def _parse(self, raw: str, persona: Persona, intent: Intent) -> list[dict[str, Any]]:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]
        try:
            data = json.loads(text.strip())
        except json.JSONDecodeError:
            logger.error("Failed to parse LLM response as JSON")
            return []

        items = data.get("test_cases", [])
        results: list[dict[str, Any]] = []
        for item in items:
            prompt_text = item.get("prompt_text", "")
            if not prompt_text:
                continue
            results.append(TestCasePrompt(
                persona_id=persona.id,
                intent_id=intent.id,
                prompt_text=prompt_text,
            ).model_dump())
        return results