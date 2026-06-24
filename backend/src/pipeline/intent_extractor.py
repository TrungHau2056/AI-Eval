import json
import logging
from typing import Any, TypedDict, Literal

from langgraph.graph import END, START, StateGraph

from src.chunking.text_chunker import chunk_text
from src.llm.base import LLMClient
from src.memory.base import BaseMemory
from src.memory.conversation_memory import ConversationMemory
from src.models.schemas import Intent, RawInput
from src.observability.langfuse import capture_io_enabled, langfuse_observation

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


class IntentState(TypedDict):
    raw_input: RawInput
    guidance: str
    chunks: list[str]
    current_chunk_idx: int
    all_intents: list[dict[str, Any]]
    final_intents: list[dict[str, Any]]


class IntentAgent:
    def __init__(self, llm: LLMClient, memory: BaseMemory | None = None, max_chunk_tokens: int = 50000):
        self.llm = llm
        self.memory = memory or ConversationMemory()
        self.max_chunk_tokens = max_chunk_tokens
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(IntentState)
        workflow.add_node("prepare_chunks", self._prepare_chunks_node)
        workflow.add_node("extract_intents_chunk", self._extract_intents_chunk_node)
        workflow.add_node("deduplicate_intents", self._deduplicate_intents_node)

        workflow.add_edge(START, "prepare_chunks")
        workflow.add_edge("prepare_chunks", "extract_intents_chunk")
        workflow.add_conditional_edges(
            "extract_intents_chunk",
            self._route_next_chunk,
            ["extract_intents_chunk", "deduplicate_intents"]
        )
        workflow.add_edge("deduplicate_intents", END)
        return workflow.compile()

    def _prepare_chunks_node(self, state: IntentState) -> dict[str, Any]:
        raw_content = state["raw_input"].content
        chunks = chunk_text(raw_content, max_tokens=self.max_chunk_tokens)
        logger.info("IntentGraph | prepare_chunks | total_chunks=%d", len(chunks))
        return {
            "chunks": chunks,
            "current_chunk_idx": 0,
            "all_intents": [],
            "final_intents": []
        }

    async def _extract_intents_chunk_node(self, state: IntentState) -> dict[str, Any]:
        idx = state["current_chunk_idx"]
        chunks = state["chunks"]
        guidance = state["guidance"]
        
        chunk = chunks[idx]
        logger.info("IntentGraph | extract_intents_chunk | chunk %d/%d (length=%d)", idx + 1, len(chunks), len(chunk))
        
        prompt = self._build_prompt(chunk, guidance)
        
        with langfuse_observation(
            "intent-extractor-chunk",
            as_type="generation",
            model=str(getattr(self.llm, "model", self.llm.__class__.__name__)),
            input=prompt if capture_io_enabled() else {"chunk_num": idx + 1, "chunk_len": len(chunk)},
            metadata={"chunk_num": idx + 1, "total_chunks": len(chunks)},
        ) as generation:
            raw = await self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT)
            intents = self._parse(raw)
            logger.info("IntentGraph | extract_intents_chunk | parsed %d intents from chunk %d", len(intents), idx + 1)
            
            generation.update(
                output=raw if capture_io_enabled() else {"intent_count": len(intents)}
            )

        self.memory.add("assistant", [it.get("intent_name", "") for it in intents])
        
        updated_intents = list(state.get("all_intents", [])) + intents
        return {
            "all_intents": updated_intents,
            "current_chunk_idx": idx + 1
        }

    def _deduplicate_intents_node(self, state: IntentState) -> dict[str, Any]:
        all_intents = state["all_intents"]
        result = self._deduplicate(all_intents)
        logger.info("IntentGraph | deduplicate_intents | raw=%d | deduped=%d", len(all_intents), len(result))
        return {
            "final_intents": result
        }

    def _route_next_chunk(self, state: IntentState) -> Literal["extract_intents_chunk", "deduplicate_intents"]:
        if state["current_chunk_idx"] < len(state["chunks"]):
            return "extract_intents_chunk"
        return "deduplicate_intents"

    async def run(self, raw_input: RawInput, guidance: str = "") -> list[dict[str, Any]]:
        logger.info("IntentAgent.run() via LangGraph | input_length=%d | guidance=%s", len(raw_input.content), bool(guidance))
        if guidance:
            self.memory.add("user", guidance)

        with langfuse_observation(
            "intent-extraction",
            as_type="span",
            input={"input_length": len(raw_input.content), "guidance_provided": bool(guidance)},
            metadata={"stage": "intent_extraction", "architecture": "langgraph"},
        ) as span:
            initial_state: IntentState = {
                "raw_input": raw_input,
                "guidance": guidance,
                "chunks": [],
                "current_chunk_idx": 0,
                "all_intents": [],
                "final_intents": []
            }
            final_state = await self.graph.ainvoke(initial_state)
            result = final_state.get("final_intents", [])
            span.update(
                output={"intent_count": len(result)}
            )
            return result

    async def run_single(self, raw_input: RawInput, guidance: str = "") -> list[dict[str, Any]]:
        logger.info("IntentAgent.run_single() via LangGraph | input_length=%d | guidance=%s", len(raw_input.content), bool(guidance))
        return await self.run(raw_input, guidance)

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
        seen: set[str] = set()
        result: list[dict[str, Any]] = []
        for intent in intents:
            key = intent["intent_name"].strip().lower()
            if key not in seen:
                seen.add(key)
                result.append(intent)
        return result
