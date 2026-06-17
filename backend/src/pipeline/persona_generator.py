import json
import logging
from typing import Any

from src.llm.base import LLMClient
from src.memory.base import BaseMemory
from src.memory.conversation_memory import ConversationMemory
from src.models.schemas import Intent, Persona

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """# ROLE
Bạn là một Senior UX Researcher chuyên nghiệp. Nhiệm vụ của bạn là nhận vào MỘT DANH SÁCH (Array) các Intents, từ đó VỚI MỖI Intent, xây dựng đúng 2 Persona (Chân dung người dùng) có hành vi và tâm lý hoàn toàn trái ngược nhau để phục vụ việc tạo bộ kịch bản kiểm thử.

# QUY TẮC BẮT BUỘC (TIÊU CHÍ NGHIỆM THU MỨC 4)

1. VÒNG LẶP ĐẦY ĐỦ (Full Batch Processing): Bạn BẮT BUỘC phải duyệt qua TOÀN BỘ danh sách Intents đầu vào. Nếu input có N Intents, bạn phải trả về chính xác `2 * N` Personas. Tuyệt đối không được bỏ sót hoặc tóm tắt.

2. ĐỊNH NGHĨA PERSONA DỰA TRÊN HÀNH VI: Một Persona KHÔNG phải là bảng mô tả nhân khẩu học (Tuổi, giới tính, nghề nghiệp chung chung) hay copy lời quảng cáo. Một Persona bắt buộc phải cấu thành từ 5 thông tin:
   - Trigger: Hoàn cảnh/thời điểm kích hoạt nhu cầu.
   - Utterance: Câu gõ mẫu tương ứng của persona đó.
   - Tần suất: Nhịp độ sử dụng (phải có con số và thời gian cụ thể).
   - Pain: Vướng mắc, khó khăn thực tế của họ.
   - Reject: Đối tượng, giải pháp họ tuyệt đối KHÔNG quan tâm và lý do.

3. TÍNH ĐỐI LẬP TUYỆT ĐỐI (Inter-Persona Divergence): Với mỗi intent, 2 Persona sinh ra phải khác nhau ít nhất 3/5 khía cạnh thông tin trên. Trong đó, BẮT BUỘC phải khác biệt hoàn toàn về bản chất ở 2 khía cạnh: [Trigger (Hoàn cảnh)] và [Utterance Register (Giọng điệu/Cách hành văn)].
   - Persona A (Happy-path / Thuận lợi): Người dùng casual, kiên nhẫn, rành công nghệ, gõ từ ngữ lịch sự, đầy đủ thông tin.
   - Persona B (Edge-case / Nghiệt ngã): Người dùng khẩn cấp, vội vã, mù công nghệ, gõ không dấu, dùng từ mơ hồ hoặc liên tục hỏi vặn vẹo.

4. SỰ NHẤT QUÁN NỘI BỘ (Internal Consistency): Câu chuyện của từng Persona phải tuyệt đối chặt chẽ và ăn nhập logic với nhau. Lối sống, nỗi đau và tần suất không được đá nhau.

5. BIÊN GIỚI TỪ CHỐI RÕ RÀNG (Falsifiable Reject): Mục Reject KHÔNG được viết hời hợt, generic. Tiêu chí này bắt buộc phải chỉ rõ một đối tượng cụ thể và được TIE (gắn liền) một cách hợp lý với hoàn cảnh sống/tần suất của Persona đó.

Trả về JSON theo đúng schema yêu cầu, không thêm text nào khác."""

USER_PROMPT = """Xây dựng 2 Persona đối lập cho danh sách Intents sau:

**Danh sách Intents:**
{intents_json}

{guidance}{memory_context}

Trả về JSON dạng:
{{
  "personas": [
    {{
      "intent_num": 1,
      "intent_name": "Tên intent kế thừa từ input",
      "persona_num": 1,
      "persona_type": "happy-path",
      "trigger": "Mô tả hoàn cảnh thuận lợi kích hoạt",
      "utterance": "Câu chat mẫu tương ứng (Lịch sự, đủ ý)",
      "frequency": "Tần suất cụ thể kèm mốc thời gian",
      "pain": "Nỗi đau/vướng mắc riêng",
      "reject": "Đối tượng từ chối cụ thể + Lý do",
      "special_situation": "Tình huống đặc biệt nếu có",
      "research_source": "Nguồn giả định",
      "why_different": "Lý giải vì sao chân dung này khác biệt hoàn toàn với nhóm còn lại",
      "expected_behavior": "Hành vi hoặc nhu cầu kỳ vọng cốt lõi",
      "ai_response_example": "Ví dụ ngắn cách AI nên phản hồi Persona này"
    }},
    {{
      "intent_num": 1,
      "intent_name": "Tên intent kế thừa từ input",
      "persona_num": 2,
      "persona_type": "edge-case",
      "trigger": "Mô tả hoàn cảnh khẩn cấp/nghiệt ngã",
      "utterance": "Câu chat mẫu tương ứng (Cụt lủn, viết tắt, không dấu...)",
      "frequency": "Tần suất cụ thể kèm mốc thời gian",
      "pain": "Nỗi đau/vướng mắc riêng",
      "reject": "Đối tượng từ chối cụ thể + Lý do",
      "special_situation": "Tình huống đặc biệt nếu có",
      "research_source": "Nguồn giả định",
      "why_different": "Lý giải sự đối lập với Persona 1",
      "expected_behavior": "Hành vi kỳ vọng",
      "ai_response_example": "Cách AI phải khéo léo xử lý Edge-case này"
    }}
  ]
}}"""


class PersonaAgent:
    def __init__(self, llm: LLMClient, memory: BaseMemory | None = None):
        self.llm = llm
        self.memory = memory or ConversationMemory()

    async def run(self, intents: list[Intent], guidance: str = "") -> list[dict[str, Any]]:
        logger.info("PersonaAgent.run() | num_intents=%d | guidance=%s", len(intents), bool(guidance))
        if guidance:
            self.memory.add("user", guidance)

        intents_json = json.dumps(
            [{"intent_num": i.intent_num, "intent_name": i.intent_name, "moment": i.moment, "utterance": i.utterance}
             for i in intents],
            ensure_ascii=False, indent=2
        )

        all_personas: list[dict[str, Any]] = []
        prompt = self._build_prompt(intents_json, guidance)
        logger.info("Calling LLM.generate() for persona generation ...")
        raw = await self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT)
        logger.info("LLM responded | response_length=%d", len(raw))
        personas = self._parse(raw, intents)
        logger.info("Parsed %d personas", len(personas))

        self.memory.add("assistant", [p.get("persona_type", "") for p in personas])
        all_personas.extend(personas)

        return all_personas

    async def run_single(self, intent: Intent, guidance: str = "") -> list[dict[str, Any]]:
        logger.info("PersonaAgent.run_single() | intent=%s | guidance=%s", intent.intent_name, bool(guidance))
        if guidance:
            self.memory.add("user", guidance)

        intents_json = json.dumps(
            [{"intent_num": intent.intent_num, "intent_name": intent.intent_name, "moment": intent.moment, "utterance": intent.utterance}],
            ensure_ascii=False, indent=2
        )

        prompt = self._build_prompt(intents_json, guidance)
        logger.info("Calling LLM.generate() for single persona ...")
        raw = await self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT)
        logger.info("LLM responded | response_length=%d", len(raw))
        personas = self._parse(raw, [intent])
        logger.info("Parsed %d personas", len(personas))

        self.memory.add("assistant", [p.get("persona_type", "") for p in personas])

        return personas

    def add_feedback(self, feedback: str) -> None:
        self.memory.add("feedback", feedback)

    def clear_memory(self) -> None:
        self.memory.clear()

    def _build_prompt(self, intents_json: str, guidance: str) -> str:
        memory_context = ""
        ctx = self.memory.get_context()
        if ctx:
            memory_context = f"\n\n**Lich su / Goi y tu truoc:**\n{ctx}"

        return USER_PROMPT.format(
            intents_json=intents_json,
            guidance=f"Huong dan them: {guidance}" if guidance else "",
            memory_context=memory_context,
        )

    def _parse(self, raw: str, intents: list[Intent]) -> list[dict[str, Any]]:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]
        try:
            data = json.loads(text.strip())
        except json.JSONDecodeError:
            logger.error("Failed to parse LLM response as JSON | raw_preview=%s", raw[:300])
            return []

        items = data.get("personas", data if isinstance(data, list) else [])
        intent_map = {i.intent_num: i for i in intents if i.intent_num}
        results: list[dict[str, Any]] = []

        for item in items:
            persona_type = item.get("persona_type", "")
            if not persona_type:
                continue

            inum = item.get("intent_num", 0)
            intent = intent_map.get(inum)
            intent_id = intent.id if intent else (intents[0].id if intents else "")

            trait = "easy" if "happy" in persona_type.lower() else "hard"
            trigger = item.get("trigger", "")
            utterance = item.get("utterance", "")
            pain = item.get("pain", "")

            results.append(Persona(
                intent_id=intent_id,
                intent_num=inum,
                intent_name=item.get("intent_name", ""),
                persona_num=item.get("persona_num", 0),
                persona_type=persona_type,
                trigger=trigger,
                utterance=utterance,
                frequency=item.get("frequency", ""),
                pain=pain,
                reject=item.get("reject", ""),
                special_situation=item.get("special_situation", ""),
                research_source=item.get("research_source", ""),
                why_different=item.get("why_different", ""),
                expected_behavior=item.get("expected_behavior", ""),
                ai_response_example=item.get("ai_response_example", ""),
                name=f"{'Happy-path' if trait == 'easy' else 'Edge-case'} - {item.get('intent_name', '')}",
                description=f"Trigger: {trigger} | Pain: {pain}",
                trait_type=trait,
            ).model_dump())
        return results