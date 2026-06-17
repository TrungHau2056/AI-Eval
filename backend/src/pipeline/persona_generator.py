import json
import logging
from typing import Any

from src.llm.base import LLMClient
from src.memory.base import BaseMemory
from src.memory.conversation_memory import ConversationMemory
from src.models.schemas import Intent, Persona

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Bạn là chuyên gia tạo persona thử nghiệm AI. Nhiệm vụ của bạn là tạo ra các persona đối lập để test AI một cách toàn diện.
Mỗi Intent cần 2 Persona:
- 1 persona "easy": người dùng dễ tính, hợp tác, rõ ràng trong yêu cầu
- 1 persona "hard": người dùng khó tính, thiếu kiên nhẫn, yêu cầu mơ hồ hoặc khó hiểu

Persona phải chi tiết, chân thực, dựa trên evidence từ phản hồi thật của người dùng.

Trả về JSON theo đúng schema yêu cầu, không thêm text nào khác."""

USER_PROMPT = """Với Intent sau, tạo 2 persona trái ngược nhau:

**Intent:**
- Bối cảnh: {context}
- Mục tiêu: {goal}
- Evidence: {evidence}

{guidance}{memory_context}

Trả về JSON dạng:
{{
  "personas": [
    {{"name": "...", "description": "...", "trait_type": "easy"}},
    {{"name": "...", "description": "...", "trait_type": "hard"}}
  ]
}}"""


class PersonaAgent:
    def __init__(self, llm: LLMClient, memory: BaseMemory | None = None):
        self.llm = llm
        self.memory = memory or ConversationMemory()

    async def run(self, intents: list[Intent], guidance: str = "") -> list[dict[str, Any]]:
        if guidance:
            self.memory.add("user", guidance)

        all_personas: list[dict[str, Any]] = []
        for intent in intents:
            logger.info(f"Generating personas for intent: {intent.goal}")
            prompt = self._build_prompt(intent, guidance)
            raw = await self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT)
            personas = self._parse(raw, intent.id)

            self.memory.add("assistant", [p["name"] for p in personas])

            all_personas.extend(personas)

        return all_personas

    async def run_single(self, intent: Intent, guidance: str = "") -> list[dict[str, Any]]:
        if guidance:
            self.memory.add("user", guidance)

        prompt = self._build_prompt(intent, guidance)
        raw = await self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT)
        personas = self._parse(raw, intent.id)

        self.memory.add("assistant", [p["name"] for p in personas])

        return personas

    def add_feedback(self, feedback: str) -> None:
        self.memory.add("feedback", feedback)

    def clear_memory(self) -> None:
        self.memory.clear()

    def _build_prompt(self, intent: Intent, guidance: str) -> str:
        memory_context = ""
        ctx = self.memory.get_context()
        if ctx:
            memory_context = f"\n\n**Lịch sử / Gợi ý từ trước:**\n{ctx}"

        return USER_PROMPT.format(
            context=intent.context,
            goal=intent.goal,
            evidence=", ".join(intent.evidence) if intent.evidence else "N/A",
            guidance=f"Hướng dẫn thêm: {guidance}" if guidance else "",
            memory_context=memory_context,
        )

    def _parse(self, raw: str, intent_id: str) -> list[dict[str, Any]]:
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
        results: list[dict[str, Any]] = []
        for item in items:
            name = item.get("name", "")
            description = item.get("description", "")
            if not name or not description:
                continue
            results.append(Persona(
                intent_id=intent_id,
                name=name,
                description=description,
                trait_type=item.get("trait_type", "easy"),
            ).model_dump())
        return results