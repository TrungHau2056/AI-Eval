import logging
from typing import Any

from src.llm.base import LLMClient
from src.memory.base import BaseMemory
from src.memory.conversation_memory import ConversationMemory
from src.models.schemas import Intent
from src.pipeline.persona_graph import PersonaGenerationGraph

logger = logging.getLogger(__name__)


class PersonaAgent:
    def __init__(
        self,
        llm: LLMClient,
        memory: BaseMemory | None = None,
        max_iterations: int = 5,
        pass_threshold: float = 0.75,
    ):
        self.llm = llm
        self.memory = memory or ConversationMemory()
        self.max_iterations = max_iterations
        self.pass_threshold = pass_threshold

    async def run(self, intents: list[Intent], guidance: str = "", trace_id: str | None = None) -> list[dict[str, Any]]:
        personas, _ = await self._run_graph(intents, guidance, trace_id)
        return personas

    async def run_with_diagnostics(
        self, intents: list[Intent], guidance: str = "", trace_id: str | None = None
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        return await self._run_graph(intents, guidance, trace_id)

    async def _run_graph(
        self, intents: list[Intent], guidance: str = "", trace_id: str | None = None
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        logger.info("PersonaAgent.run() | num_intents=%d | guidance=%s", len(intents), bool(guidance))
        if guidance:
            self.memory.add("user", guidance)

        graph = PersonaGenerationGraph(
            self.llm,
            max_iterations=self.max_iterations,
            pass_threshold=self.pass_threshold,
        )
        final_state = await graph.run(
            intents,
            guidance=guidance,
            memory_context=self.memory.get_context(),
            trace_id=trace_id,
        )
        personas = final_state.get("personas", [])
        evaluation = final_state.get("evaluation", {})
        failure_summary = final_state.get("failure_summary", [])
        logger.info(
            "PersonaAgent graph completed | personas=%d | approved=%s | score=%s | unresolved=%d",
            len(personas),
            evaluation.get("approved"),
            evaluation.get("score"),
            len(failure_summary),
        )

        self.memory.add("assistant", [p.get("persona_type", "") for p in personas])
        return personas, failure_summary

    async def run_single(self, intent: Intent, guidance: str = "", trace_id: str | None = None) -> list[dict[str, Any]]:
        logger.info("PersonaAgent.run_single() | intent=%s | guidance=%s", intent.intent_name, bool(guidance))
        if guidance:
            self.memory.add("user", guidance)

        graph = PersonaGenerationGraph(
            self.llm,
            max_iterations=self.max_iterations,
            pass_threshold=self.pass_threshold,
        )
        final_state = await graph.run(
            [intent],
            guidance=guidance,
            memory_context=self.memory.get_context(),
            trace_id=trace_id,
        )
        personas = final_state.get("personas", [])
        evaluation = final_state.get("evaluation", {})
        logger.info(
            "PersonaAgent single graph completed | personas=%d | approved=%s | score=%s",
            len(personas),
            evaluation.get("approved"),
            evaluation.get("score"),
        )

        self.memory.add("assistant", [p.get("persona_type", "") for p in personas])

        return personas

    def add_feedback(self, feedback: str) -> None:
        self.memory.add("feedback", feedback)

    def clear_memory(self) -> None:
        self.memory.clear()
