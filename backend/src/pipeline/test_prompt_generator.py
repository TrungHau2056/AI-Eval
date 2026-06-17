import json
import logging
from typing import Any

from src.llm.base import LLMClient
from src.memory.base import BaseMemory
from src.memory.conversation_memory import ConversationMemory
from src.models.schemas import Intent, Persona, TestCasePrompt

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """# ROLE
Bạn là một Senior QA Automation Engineer chuyên kiểm thử hệ thống AI. Nhiệm vụ của bạn là nhận thông tin về một Persona và một Intent cụ thể, từ đó thiết kế đúng 1 Kịch bản kiểm thử (Test Case) sắc bén, bám sát 100% cấu trúc cơ sở dữ liệu kiểm thử của dự án.

# QUY TẮC BẮT BUỘC (TEST CASE DESIGN RULES)

1. SỐ LƯỢNG ĐẦU RA CỐ ĐỊNH: Mỗi lần gọi API này BẮT BUỘC trả về đúng 1 Test Case trong mảng `test_cases`. Không được sinh 0 hoặc nhiều hơn 1 Test Case trên mỗi lần gọi.

2. MÔ PHỎNG "START" (User Utterance):
   - Trường `start` chính là câu chat giả lập của người dùng để nạp vào chatbot. BẮT BUỘC kế thừa giọng điệu từ Persona.
   - Phải giữ đúng "VN Reality" (viết thường, viết tắt, từ đệm, lỗi chính tả cố ý nếu Persona là nhóm khó tính/vội vã).
   - Ví dụ ĐÚNG (Happy-path): "cho mình hỏi trạm sạc ở quận 7 còn chỗ k ạ"
   - Ví dụ ĐÚNG (Edge-case): "sac o dau day troi oi pin sap het roi"

3. ĐỊNH NGHĨA "END EXPECTED OUTCOME" (Tiêu chí nghiệm thu):
   - Trường `end_expected_outcome` phải là một đoạn văn bản chỉ dẫn rõ ràng cho Tester, bao gồm 2 vế logic:
     + [MUST HAVE]: Hành động AI bắt buộc phải làm. Phải cụ thể, đếm được.
     + [MUST NOT HAVE / BOUNDARY]: Bẫy giới hạn bám sát đặc điểm Persona.
   - Ví dụ SAI: "AI phải trả lời hữu ích và thân thiện."
   - Ví dụ ĐÚNG: "[MUST HAVE] AI phản hồi trong vòng 1 lượt, trả về 2-3 trạm sạc còn trống gần nhất kèm khoảng cách ước tính. [MUST NOT HAVE] AI không gợi ý trạm cách >2km; không dùng từ ngữ kỹ thuật như 'DC fast charging port'."

4. BỐI CẢNH & TÂM LÝ:
   - Tóm tắt tâm lý người dùng vào trường `title_user_moment` (Ai? Đang bị gì? Muốn gì?).
   - Viết rõ mục tiêu vào trường `goal` để Tester hiểu kỳ vọng cuối cùng của người dùng.

Trả về JSON theo đúng schema yêu cầu, không thêm text nào khác."""

USER_PROMPT = """Thiết kế 1 Test Case cho cặp Persona-Intent sau:

**Intent:**
- Intent Num: {intent_num}
- Intent Name: {intent_name}

**Persona Details:**
{persona_json}

{guidance}{memory_context}

Trả về JSON dạng:
{{
  "test_cases": [
    {{
      "intent_num": {intent_num},
      "intent_name": "{intent_name}",
      "case_num": {persona_num},
      "title_user_moment": "Tóm tắt ngắn gọn hoàn cảnh (Ai? Đang bị gì? Muốn gì?)",
      "persona": "Mô tả chi tiết user kế thừa từ input Persona",
      "goal": "Mục tiêu cụ thể của người dùng",
      "start": "Câu chat giả lập của người dùng nạp vào chatbot",
      "end_expected_outcome": "Mô tả chi tiết [MUST HAVE] và [MUST NOT HAVE] theo đúng Persona"
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

        logger.info("TestCaseAgent.run() | num_personas=%d | num_intents=%d | guidance=%s", len(personas), len(intents), bool(guidance))

        if guidance:
            self.memory.add("user", guidance)

        for idx, persona in enumerate(personas):
            intent = intent_map.get(persona.intent_id)
            if not intent:
                logger.warning("Skipping persona %s: no matching intent found (intent_id=%s)", persona.id, persona.intent_id)
                continue

            logger.info("Generating test case %d/%d | persona_type=%s | intent=%s", idx + 1, len(personas), persona.persona_type, persona.intent_name)
            prompt = self._build_prompt(persona, intent, guidance)
            logger.info("Calling LLM.generate() for test case %d ...", idx + 1)
            raw = await self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT)
            logger.info("LLM responded for test case %d | response_length=%d", idx + 1, len(raw))
            test_cases = self._parse(raw, persona, intent)
            logger.info("Parsed %d test cases from persona %d", len(test_cases), idx + 1)

            self.memory.add("assistant", [tc.get("start", "") for tc in test_cases])

            all_test_cases.extend(test_cases)

        logger.info("TestCaseAgent.run() done | total=%d test cases", len(all_test_cases))
        return all_test_cases

    async def run_single(self, persona: Persona, intent: Intent, guidance: str = "") -> list[dict[str, Any]]:
        logger.info("TestCaseAgent.run_single() | persona=%s | intent=%s | guidance=%s", persona.persona_type, intent.intent_name, bool(guidance))
        if guidance:
            self.memory.add("user", guidance)

        prompt = self._build_prompt(persona, intent, guidance)
        logger.info("Calling LLM.generate() for single test case ...")
        raw = await self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT)
        logger.info("LLM responded | response_length=%d", len(raw))
        test_cases = self._parse(raw, persona, intent)
        logger.info("Parsed %d test cases", len(test_cases))

        self.memory.add("assistant", [tc.get("start", "") for tc in test_cases])

        return test_cases

    def add_feedback(self, feedback: str) -> None:
        self.memory.add("feedback", feedback)

    def clear_memory(self) -> None:
        self.memory.clear()

    def _build_prompt(self, persona: Persona, intent: Intent, guidance: str) -> str:
        memory_context = ""
        ctx = self.memory.get_context()
        if ctx:
            memory_context = f"\n\n**Lich su / Goi y tu truoc:**\n{ctx}"

        persona_json = json.dumps({
            "persona_num": persona.persona_num,
            "persona_type": persona.persona_type,
            "trigger": persona.trigger,
            "utterance": persona.utterance,
            "frequency": persona.frequency,
            "pain": persona.pain,
            "reject": persona.reject,
            "expected_behavior": persona.expected_behavior,
            "ai_response_example": persona.ai_response_example,
        }, ensure_ascii=False, indent=2)

        return USER_PROMPT.format(
            intent_num=intent.intent_num or 1,
            intent_name=intent.intent_name or intent.goal,
            persona_num=persona.persona_num or 1,
            persona_json=persona_json,
            guidance=f"Huong dan them: {guidance}" if guidance else "",
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
            logger.error("Failed to parse LLM response as JSON | raw_preview=%s", raw[:300])
            return []

        items = data.get("test_cases", [])
        results: list[dict[str, Any]] = []
        for item in items:
            start = item.get("start", "")
            end_expected = item.get("end_expected_outcome", "")
            if not start:
                continue
            results.append(TestCasePrompt(
                persona_id=persona.id,
                intent_id=intent.id,
                intent_num=item.get("intent_num", intent.intent_num),
                intent_name=item.get("intent_name", intent.intent_name),
                case_num=item.get("case_num", persona.persona_num),
                title_user_moment=item.get("title_user_moment", ""),
                persona=item.get("persona", persona.description),
                goal=item.get("goal", ""),
                start=start,
                end_expected_outcome=end_expected,
                prompt_text=start,
            ).model_dump())
        return results