import json
import logging
from typing import Any

from src.llm.base import LLMClient
from src.memory.base import BaseMemory
from src.memory.conversation_memory import ConversationMemory
from src.models.schemas import Intent, Persona, TestCasePrompt
from src.observability.langfuse import capture_io_enabled, langfuse_observation
from src.prompts.loader import TESTCASE_SYSTEM, TESTCASE_USER

logger = logging.getLogger(__name__)


class TestCaseAgent:
    def __init__(self, llm: LLMClient, memory: BaseMemory | None = None):
        self.llm = llm
        self.memory = memory or ConversationMemory()

    async def run(
        self,
        personas: list[Persona],
        intents: list[Intent],
        guidance: str = "",
        trace_id: str | None = None,
    ) -> list[dict[str, Any]]:
        logger.info(
            "TestCaseAgent.run() | num_personas=%d | num_intents=%d | guidance=%s",
            len(personas),
            len(intents),
            bool(guidance),
        )
        if guidance:
            self.memory.add("user", guidance)

        prompt = self._build_prompt(personas, intents, guidance)

        with langfuse_observation(
            "test-case-generation",
            as_type="generation",
            model=str(getattr(self.llm, "model", self.llm.__class__.__name__)),
            input=prompt if capture_io_enabled() else {
                "persona_count": len(personas),
                "intent_count": len(intents),
            },
            metadata={
                "stage": "test_case_generation",
                "persona_count": len(personas),
                "intent_count": len(intents),
            },
            trace_id=trace_id,
        ) as generation:
            raw = await self.llm.generate(prompt, system_prompt=TESTCASE_SYSTEM)
            test_cases = self._parse(raw, personas, intents)
            logger.info("TestCaseAgent.run() done | total=%d test cases", len(test_cases))
            generation.update(
                output=raw if capture_io_enabled() else {"test_case_count": len(test_cases)}
            )

        self.memory.add("assistant", [tc.get("start", "") for tc in test_cases])
        return test_cases

    async def run_single(
        self,
        persona: Persona,
        intent: Intent,
        guidance: str = "",
        trace_id: str | None = None,
    ) -> list[dict[str, Any]]:
        logger.info(
            "TestCaseAgent.run_single() | persona=%s | intent=%s | guidance=%s",
            persona.persona_type,
            intent.intent_name,
            bool(guidance),
        )
        return await self.run([persona], [intent], guidance, trace_id=trace_id)

    def add_feedback(self, feedback: str) -> None:
        self.memory.add("feedback", feedback)

    def clear_memory(self) -> None:
        self.memory.clear()

    def _build_prompt(
        self, personas: list[Persona], intents: list[Intent], guidance: str
    ) -> str:
        memory_context = ""
        ctx = self.memory.get_context()
        if ctx:
            memory_context = f"\n\n**Lich su / Goi y tu truoc:**\n{ctx}"

        intents_json = json.dumps(
            [
                {
                    "intent_num": i.intent_num,
                    "intent_name": i.intent_name,
                }
                for i in intents
            ],
            ensure_ascii=False,
            indent=2,
        )

        personas_json = json.dumps(
            [
                {
                    "persona_num": p.persona_num,
                    "intent_num": p.intent_num,
                    "intent_name": p.intent_name,
                    "persona_type": p.persona_type,
                    "trigger": p.trigger,
                    "utterance": p.utterance,
                    "frequency": p.frequency,
                    "pain": p.pain,
                    "reject": p.reject,
                    "expected_behavior": p.expected_behavior,
                    "ai_response_example": p.ai_response_example,
                }
                for p in personas
            ],
            ensure_ascii=False,
            indent=2,
        )

        return TESTCASE_USER.format(
            intents_json=intents_json,
            personas_json=personas_json,
            guidance=f"Huong dan them: {guidance}" if guidance else "",
            memory_context=memory_context,
        )

    def _parse(
        self, raw: str, personas: list[Persona], intents: list[Intent]
    ) -> list[dict[str, Any]]:
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
        persona_map = {(p.intent_num, p.persona_num): p for p in personas}
        intent_map = {i.id: i for i in intents}
        intent_name_map = {i.intent_name: i for i in intents}

        results: list[dict[str, Any]] = []
        for item in items:
            start = item.get("start") or ""
            if not start:
                continue

            inum = item.get("intent_num")
            pnum = item.get("persona_num")
            persona = persona_map.get((inum, pnum))
            if not persona:
                intent_name = item.get("intent_name", "")
                matching = [p for p in personas if p.intent_name == intent_name]
                if matching:
                    persona = matching[0]
            if not persona:
                logger.warning(
                    "Could not match test case to persona | intent_num=%s persona_num=%s",
                    inum,
                    pnum,
                )
                continue

            intent = intent_map.get(persona.intent_id) or intent_name_map.get(persona.intent_name)
            if not intent:
                logger.warning("Could not match test case to intent | persona_id=%s", persona.id)
                continue

            results.append(
                TestCasePrompt(
                    persona_id=persona.id,
                    intent_id=intent.id,
                    intent_num=item.get("intent_num", intent.intent_num),
                    intent_name=item.get("intent_name") or intent.intent_name,
                    case_num=item.get("case_num", persona.persona_num),
                    title_user_moment=item.get("title_user_moment") or "",
                    persona=item.get("persona") or persona.description,
                    goal=item.get("goal") or "",
                    start=start,
                    end_expected_outcome=item.get("end_expected_outcome") or "",
                    prompt_text=start,
                ).model_dump()
            )
        return results
