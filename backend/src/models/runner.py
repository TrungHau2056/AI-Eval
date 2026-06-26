"""
Persona Agent Runner
=====================
Chạy agent loop cho nhiều intent, aggregate kết quả.

Tách biệt khỏi agent_loop.py để dễ test từng phần.
"""
import asyncio
import logging
from typing import Callable

from ..llm.base import PersonaAgentLLMBase
from ..schemas.models import (
    AgentLoopResult,
    IntentInput,
    PersonaAgentResult,
    RubricInput,
)
from .agent_loop import PersonaAgentLoop

logger = logging.getLogger(__name__)


class PersonaAgentRunner:
    """
    Runner xử lý nhiều intent qua agent loop.

    Usage:
        runner = PersonaAgentRunner(llm=client, max_iterations=3)
        result = await runner.run_all(intents, rubric)
    """

    def __init__(
        self,
        llm: PersonaAgentLLMBase,
        max_iterations: int = 3,
        on_progress: Callable[[str], None] | None = None,
    ):
        self.llm = llm
        self.max_iterations = max_iterations
        self.on_progress = on_progress or (lambda msg: None)

    async def run_all(
        self,
        intents: list[IntentInput],
        rubric: RubricInput,
        guidance: str = "",
    ) -> PersonaAgentResult:
        """
        Chạy agent loop cho tất cả intents.
        Xử lý sequential để tránh rate limit (có thể đổi thành parallel sau).
        """
        self.on_progress(
            f"\n🎯 Bắt đầu PersonaAgent cho {len(intents)} intent(s)...\n"
            f"   Rubric: {rubric.name} ({rubric.version})\n"
            f"   Pass threshold: {rubric.pass_threshold:.0%}\n"
            f"   Max iterations: {self.max_iterations}\n"
        )

        loop = PersonaAgentLoop(
            llm=self.llm,
            max_iterations=self.max_iterations,
            on_progress=self.on_progress,
        )

        results: list[AgentLoopResult] = []
        for i, intent in enumerate(intents, 1):
            self.on_progress(
                f"\n[{i}/{len(intents)}] Intent: '{intent.goal}'\n"
                f"  Context: {intent.context}\n"
            )
            try:
                result = await loop.run(intent, rubric, guidance)
                results.append(result)
            except Exception as e:
                logger.error(f"Agent loop failed for intent '{intent.goal}': {e}")
                results.append(
                    AgentLoopResult(
                        intent_id=intent.id,
                        intent_goal=intent.goal,
                        passed=False,
                        failure_reason=f"Unexpected error: {e}",
                    )
                )

        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed

        self.on_progress(
            f"\n{'='*60}\n"
            f"✅ Hoàn thành! {passed}/{len(results)} intent(s) đạt yêu cầu.\n"
            f"{'='*60}\n"
        )

        return PersonaAgentResult(
            intent_results=results,
            total_intents=len(results),
            passed_intents=passed,
            failed_intents=failed,
        )
