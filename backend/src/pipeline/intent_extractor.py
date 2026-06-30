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
from src.prompts.loader import INTENT_SYSTEM, INTENT_USER

logger = logging.getLogger(__name__)


class IntentState(TypedDict):
    raw_input: RawInput
    guidance: str
    chunks: list[str]
    current_chunk_idx: int
    all_intents: list[dict[str, Any]]
    final_intents: list[dict[str, Any]]
    trace_id: str
    parent_span_id: str


class IntentAgent:
    def __init__(self, llm: LLMClient, memory: BaseMemory | None = None, max_chunk_tokens: int = 50000, system_prompt: str | None = None, user_template: str | None = None):
        self.llm = llm
        self.memory = memory or ConversationMemory()
        self.max_chunk_tokens = max_chunk_tokens
        self.system_prompt = system_prompt if system_prompt is not None else INTENT_SYSTEM
        self.user_template = user_template if user_template is not None else INTENT_USER
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
        raw_content = (state["raw_input"].content or "").strip()
        if not raw_content:
            logger.warning("IntentGraph | prepare_chunks | empty input content")
            return {
                "chunks": [],
                "current_chunk_idx": 0,
                "all_intents": [],
                "final_intents": [],
            }
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
        trace_id = state.get("trace_id") or None
        parent_span_id = state.get("parent_span_id") or None

        chunk = chunks[idx]
        logger.info("IntentGraph | extract_intents_chunk | chunk %d/%d (length=%d)", idx + 1, len(chunks), len(chunk))

        prompt = self._build_prompt(chunk, guidance)

        with langfuse_observation(
            "intent-extractor-chunk",
            as_type="generation",
            model=str(getattr(self.llm, "model", self.llm.__class__.__name__)),
            input=prompt if capture_io_enabled() else {"chunk_num": idx + 1, "chunk_len": len(chunk)},
            metadata={"chunk_num": idx + 1, "total_chunks": len(chunks)},
            trace_id=trace_id,
            parent_span_id=parent_span_id,
        ) as generation:
            raw = await self.llm.generate(prompt, system_prompt=self.system_prompt)
            intents = self._parse(raw)
            src_dist = {}
            for i in intents:
                s = i.get("source", "")
                src_dist[s] = src_dist.get(s, 0) + 1
            logger.info("IntentGraph | extract_intents_chunk | parsed %d intents from chunk %d | sources=%s", len(intents), idx + 1, src_dist)
            
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

    async def run(self, raw_input: RawInput, guidance: str = "", trace_id: str | None = None) -> list[dict[str, Any]]:
        logger.info("IntentAgent.run() via LangGraph | input_length=%d | guidance=%s", len(raw_input.content), bool(guidance))
        if guidance:
            self.memory.add("user", guidance)

        with langfuse_observation(
            "intent-extraction",
            as_type="span",
            input={"input_length": len(raw_input.content), "guidance_provided": bool(guidance)},
            metadata={"stage": "intent_extraction", "architecture": "langgraph"},
            trace_id=trace_id,
        ) as span:
            initial_state: IntentState = {
                "raw_input": raw_input,
                "guidance": guidance,
                "chunks": [],
                "current_chunk_idx": 0,
                "all_intents": [],
                "final_intents": [],
                "trace_id": trace_id or "",
                "parent_span_id": span.id,
            }
            final_state = await self.graph.ainvoke(initial_state)
            result = final_state.get("final_intents", [])
            span.update(
                output={"intent_count": len(result)}
            )
            return result

    async def run_single(self, raw_input: RawInput, guidance: str = "", trace_id: str | None = None) -> list[dict[str, Any]]:
        logger.info("IntentAgent.run_single() via LangGraph | input_length=%d | guidance=%s", len(raw_input.content), bool(guidance))
        return await self.run(raw_input, guidance, trace_id=trace_id)

    def add_feedback(self, feedback: str) -> None:
        self.memory.add("feedback", feedback)

    def clear_memory(self) -> None:
        self.memory.clear()

    def _build_prompt(self, raw_text: str, guidance: str) -> str:
        import collections
        memory_context = ""
        ctx = self.memory.get_context()
        if ctx:
            memory_context = f"\n\n**Lich su / Goi y tu truoc:**\n{ctx}"

        kwargs = dict(
            raw_text=raw_text,
            guidance=f"Huong dan them: {guidance}" if guidance else "",
            memory_context=memory_context,
        )
        return self.user_template.format_map(collections.defaultdict(str, kwargs))

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
            if not isinstance(item, dict):
                continue
            intent_name = (
                item.get("intent_name")
                or item.get("name")
                or item.get("title")
                or item.get("goal")
                or ""
            ).strip()
            if not intent_name:
                continue
            utterance = item.get("utterance") or item.get("typical_utterance") or ""
            moment = item.get("moment") or item.get("trigger_moment") or item.get("triggerMoment") or item.get("context") or ""
            results.append(Intent(
                intent_num=item.get("intent_num", 0),
                intent_name=intent_name,
                utterance=utterance,
                moment=moment,
                source=item.get("source") or "",
                phase=item.get("phase") or "",
                raw_observation=item.get("raw_observation") or "",
                why_valid=item.get("why_valid") or "",
                context=moment,
                goal=intent_name,
                evidence=[utterance, item.get("raw_observation") or ""],
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
