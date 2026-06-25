import json
import logging
from typing import Any

from src.chunking.text_chunker import chunk_text
from src.llm.base import LLMClient
from src.memory.base import BaseMemory
from src.memory.conversation_memory import ConversationMemory
from src.models.schemas import Intent, RawInput

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
# ROLE
Bạn là một Chuyên gia Nghiên cứu Sản phẩm AI (AI Product Researcher) thực địa xuất sắc. Bạn có năng lực bóc tách dữ liệu thô và cấu trúc hóa hành vi người dùng thành các Intent (Ý định) mang tính thực tế cao.

# TASK
Hãy phân tích dữ liệu phản hồi thô được cung cấp (comment, chat log, review). Tiến hành gom cụm các ý kiến trùng lặp và trích xuất chính xác các Intent độc lập, đặc trưng nhất của domain này.

# QUY TẮC BẮT BUỘC (TIÊU CHÍ NGHIỆM THU MỨC 4)

1. TÊN INTENT (Action Lens): Tên intent BẮT BUỘC phải viết theo cấu trúc [Verb cụ thể + Object concrete]. Tuyệt đối KHÔNG dùng tên module hoặc Noun Category nội bộ hệ thống.
   - Ví dụ SAI: "Vận tải", "Sạc xe", "Bảo hành", "Hỗ trợ", "Tư vấn".
   - Ví dụ ĐÚNG: "Đặt lịch lái thử VF8 tại showroom", "Tìm trạm sạc gần chỗ đang đứng", "Báo trạm sạc hỏng".

2. CẤP ĐỘ PHÂN RÃ (Granularity): Áp dụng test 3-câu user-observable để quyết định tách/gộp:
   - Nếu hai hành vi có mục tiêu (goal) khác nhau, thông tin hệ thống cần (info) khác nhau, HOẶC tín hiệu thành công (success signal) khác nhau -> BẮT BUỘC phải tách làm intent riêng.
   - Nếu cả 3 yếu tố trùng nhau -> GỢI Ý gộp và parameter hóa đối tượng.

3. CÂU CHAT THẬT VIỆT NAM (Authentic Utterance): Với mỗi intent, đính kèm ít nhất 1 câu mẫu người dùng gõ thật ngoài đời. Tuyệt đối KHÔNG viết câu formal, chuẩn ngữ pháp sách giáo khoa. Câu chat phải phản ánh đúng thực tế Việt Nam: cụt (bỏ chủ ngữ), viết thường (lowercase), viết tắt (k, đc, t7, cn, đg), có từ đệm cuối câu (nhé, đi, với, k), hoặc chêm tiếng Anh thông dụng.
   - Ví dụ SAI: "Tôi muốn đặt lịch lái thử xe VinFast VF8 vào cuối tuần này."
   - Ví dụ ĐÚNG: "đặt lái thử vf8 t7 ở long biên đc k"

4. ĐỘ PHỦ CHIẾN LƯỢC (Domain Coverage): Các intent phải trải đều trên ít nhất 5 giai đoạn (phase) của domain. BẮT BUỘC phải có tối thiểu 1-2 intent nằm trong phase "LỖI / KHẨN CẤP / PHỤC HỒI". Đồng thời, không có phase nào được phép chiếm quá 40% tổng số intent.

5. BỐI CẢNH KÍCH HOẠT (Trigger Moment): Mỗi intent phải đính kèm context cụ thể đáp ứng đủ 3 thông số: Where (Họ đang ở đâu?) + What doing (Họ đang làm gì?) + What worried (Họ đang lo lắng, vướng mắc điều gì?).

6. XỬ LÝ DỮ LIỆU KHÔNG ĐỦ (Fallback Behavior): Nếu dữ liệu đầu vào quá ít, KHÔNG được tự bịa thêm Intent không có bằng chứng từ data. Thay vào đó, sinh số Intent tối đa có thể xác minh được từ dữ liệu thực và thêm mục "data_gap_warning" vào JSON đầu ra.

Trả về JSON theo đúng schema yêu cầu, không thêm text nào khác."""

USER_PROMPT = """Phân tích dữ liệu phản hồi thô sau và trích xuất các Intent độc lập, đặc trưng nhất:

---
{raw_text}
---

{guidance}{memory_context}

Trả về JSON dạng:
{{
  "data_gap_warning": null,
  "intents": [
    {{
      "intent_num": 1,
      "intent_name": "Tên theo cấu trúc Verb + Object",
      "utterance": "Câu chat thực tế đời sống (VN Reality)",
      "moment": "Mô tả cụ thể dạng Where + What doing + What worried",
      "source": "Dự đoán nguồn gốc dữ liệu",
      "phase": "Tên phase thực tế trong hành trình",
      "raw_observation": "Trích dẫn hoặc tóm tắt các hành vi gốc dẫn đến Intent này",
      "why_valid": "Giải thích chi tiết lý do intent này hợp lệ"
    }}
  ]
}}
"""


class IntentAgent:
    def __init__(self, llm: LLMClient, memory: BaseMemory | None = None, max_chunk_tokens: int = 50000):
        self.llm = llm
        self.memory = memory or ConversationMemory()
        self.max_chunk_tokens = max_chunk_tokens

    async def run(self, raw_input: RawInput, guidance: str = "") -> list[dict[str, Any]]:
        logger.info("IntentAgent.run() | input_length=%d | guidance=%s", len(raw_input.content), bool(guidance))
        if guidance:
            self.memory.add("user", guidance)

        chunks = chunk_text(raw_input.content, max_tokens=self.max_chunk_tokens)
        logger.info("Chunked input into %d chunks (max_tokens=%d)", len(chunks), self.max_chunk_tokens)
        all_intents: list[dict[str, Any]] = []

        for i, chunk in enumerate(chunks):
            logger.info("Processing chunk %d/%d (length=%d)", i + 1, len(chunks), len(chunk))
            prompt = self._build_prompt(chunk, guidance)
            logger.info("Calling LLM.generate() for chunk %d ...", i + 1)
            raw = await self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT)
            logger.info("LLM responded for chunk %d | response_length=%d", i + 1, len(raw))
            intents = self._parse(raw)
            logger.info("Parsed %d intents from chunk %d", len(intents), i + 1)

            self.memory.add("assistant", [it.get("intent_name", "") for it in intents])

            all_intents.extend(intents)

        result = self._deduplicate(all_intents)
        logger.info("IntentAgent.run() done | total=%d | after_dedup=%d", len(all_intents), len(result))
        return result

    async def run_single(self, raw_input: RawInput, guidance: str = "") -> list[dict[str, Any]]:
        logger.info("IntentAgent.run_single() | input_length=%d | guidance=%s", len(raw_input.content), bool(guidance))
        if guidance:
            self.memory.add("user", guidance)

        prompt = self._build_prompt(raw_input.content, guidance)
        logger.info("Calling LLM.generate() for single intent ...")
        raw = await self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT)
        logger.info("LLM responded | response_length=%d", len(raw))
        intents = self._parse(raw)
        logger.info("Parsed %d intents", len(intents))

        self.memory.add("assistant", [it.get("intent_name", "") for it in intents])

        return intents

    def add_feedback(self, feedback: str) -> None:
        self.memory.add("feedback", feedback)

    def clear_memory(self) -> None:
        self.memory.clear()

    def _build_prompt(self, raw_text: str, guidance: str) -> str:
        memory_context = ""
        ctx = self.memory.get_context()
        if ctx:
            memory_context = f"\n\n**Lich su / Goi y tu truoc:**\n{ctx}"

        return USER_PROMPT.format(
            raw_text=raw_text,
            guidance=f"Huong dan them: {guidance}" if guidance else "",
            memory_context=memory_context,
        )

    def _parse(self, raw: str) -> list[dict[str, Any]]:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]
        try:
            data = json.loads(text.strip())
        except json.JSONDecodeError:
            logger.error("Failed to parse LLM response as JSON | raw_preview=%s", raw[:300])
            return []

        items = data.get("intents", data if isinstance(data, list) else [])
        results: list[dict[str, Any]] = []
        for item in items:
            intent_name = item.get("intent_name", "")
            if not intent_name:
                continue
            results.append(Intent(
                intent_num=item.get("intent_num", 0),
                intent_name=intent_name,
                utterance=item.get("utterance", ""),
                moment=item.get("moment", ""),
                source=item.get("source", ""),
                phase=item.get("phase", ""),
                raw_observation=item.get("raw_observation", ""),
                why_valid=item.get("why_valid", ""),
                context=item.get("moment", ""),
                goal=intent_name,
                evidence=[item.get("utterance", ""), item.get("raw_observation", "")],
            ).model_dump())
        return results

    def _deduplicate(self, intents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Dedup exact (case-insensitive) TRONG cùng 1 nguồn. Giữ bản đầu."""
        seen: set[str] = set()
        result: list[dict[str, Any]] = []
        for intent in intents:
            key = intent["intent_name"].strip().lower()
            if key not in seen:
                seen.add(key)
                result.append(intent)
        return result

    def dedup_semantic(self, intents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Hook tích hợp so khớp ngữ nghĩa (FR-B4).

        Mặc định no-op: đối chiếu chéo PRD↔data do IntentComparator đảm nhận
        (KHÔNG gộp ở đây để tránh che mất tín hiệu Confirmed). Giữ điểm cắm cho
        dedup ngữ nghĩa trong-nguồn ở vòng sau nếu cần.
        """
        return intents
