from __future__ import annotations

import json
import logging
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from src.llm.base import LLMClient
from src.models.schemas import Intent, Persona
from src.observability.langfuse import capture_io_enabled, langfuse_observation
from src.prompts.loader import (
    PERSONA_EVALUATOR_SYSTEM,
    PERSONA_EVALUATOR_USER,
    PERSONA_GENERATOR_REFINE_USER,
    PERSONA_GENERATOR_SYSTEM,
    PERSONA_GENERATOR_USER,
)

logger = logging.getLogger(__name__)


class PersonaGraphState(TypedDict, total=False):
    intents: list[Intent]
    guidance: str
    memory_context: str
    iteration: int
    max_iterations: int
    personas: list[dict[str, Any]]
    evaluation: dict[str, Any]
    revision_guidance: str
    pairs_to_regenerate: list[int]
    next_node: str
    history: list[dict[str, Any]]
    trace_id: str
    parent_span_id: str


def _strip_code_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0]
    return text.strip()


def _loads_json(raw: str) -> Any:
    return json.loads(_strip_code_fences(raw))


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _str(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _coerce_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    if score > 1.0:
        score = score / 100.0
    return max(0.0, min(score, 1.0))


def _score_from_evaluation(data: dict[str, Any]) -> float:
    # New schema (PerGent v1.3): score is a nested object with total/percent
    score_obj = data.get("score")
    if isinstance(score_obj, dict):
        percent = score_obj.get("percent")
        if percent is not None:
            return _coerce_score(percent)
        total = score_obj.get("total")
        if total is not None:
            return _coerce_score(total)

    # Old schema: flat total_score / max_score / percent
    total_score = data.get("total_score")
    max_score = data.get("max_score")
    if total_score is not None and max_score:
        try:
            return max(0.0, min(float(total_score) / float(max_score), 1.0))
        except (TypeError, ValueError, ZeroDivisionError):
            pass

    if data.get("percent") is not None:
        return _coerce_score(data.get("percent"))

    return _coerce_score(data.get("score", 0.0))


def _revision_guidance_from(data: dict[str, Any]) -> str:
    explicit = data.get("revision_guidance", "")
    if explicit:
        return explicit

    for key in ("top3_fixes", "top_fixes"):
        fixes = data.get(key, [])
        if isinstance(fixes, list) and fixes:
            return "\n".join(str(fix) for fix in fixes if fix).strip()
    return ""


def _llm_model_name(llm: LLMClient) -> str:
    return str(getattr(llm, "model", llm.__class__.__name__))


def _intent_payload(intents: list[Intent]) -> list[dict[str, Any]]:
    return [
        {
            "id": intent.id,
            "intent_num": intent.intent_num or idx + 1,
            "intent_name": intent.intent_name,
            "moment": intent.moment,
            "utterance": intent.utterance,
            "phase": intent.phase,
            "raw_observation": intent.raw_observation,
            "why_valid": intent.why_valid,
        }
        for idx, intent in enumerate(intents)
    ]


def _trace_intent_summary(intents: list[Intent]) -> dict[str, Any]:
    return {
        "intent_count": len(intents),
        "intent_names": [intent.intent_name for intent in intents],
    }


def _generation_input(payload: Any, fallback: dict[str, Any]) -> Any:
    return payload if capture_io_enabled() else fallback


def _generation_output(payload: Any, fallback: dict[str, Any]) -> Any:
    return payload if capture_io_enabled() else fallback


class PersonaGeneratorNode:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def run(self, state: PersonaGraphState) -> dict[str, Any]:
        intents = state.get("intents", [])
        iteration = state.get("iteration", 0) + 1
        existing_personas = state.get("personas", [])
        pairs_to_regenerate = state.get("pairs_to_regenerate", [])
        revision_guidance = state.get("revision_guidance", "")
        memory_context = state.get("memory_context", "")
        trace_id = state.get("trace_id") or None
        parent_span_id = state.get("parent_span_id") or None

        is_refine = bool(existing_personas and pairs_to_regenerate)

        if is_refine:
            failed_intents = [i for i in intents if (i.intent_num or 0) in pairs_to_regenerate]
            logger.info(
                "PersonaGeneratorNode | REFINE | iteration=%d | failed_intents=%d | pairs_to_regenerate=%s | trace_id=%s | parent_span_id=%s",
                iteration, len(failed_intents), pairs_to_regenerate, trace_id, parent_span_id,
            )
            prompt = self._build_refine_prompt(
                failed_intents, revision_guidance, existing_personas, pairs_to_regenerate, memory_context,
            )
            trace_input = {
                "agent": "persona_generator",
                "mode": "REFINE",
                "iteration": iteration,
                "failed_intent_count": len(failed_intents),
            }
        else:
            guidance = self._build_guidance(state)
            logger.info(
                "PersonaGeneratorNode | GENERATE | iteration=%d | intents=%d | trace_id=%s | parent_span_id=%s",
                iteration, len(intents), trace_id, parent_span_id,
            )
            prompt = self._build_prompt(intents, guidance, memory_context)
            trace_input = {
                "agent": "persona_generator",
                "mode": "GENERATE",
                "iteration": iteration,
                "guidance_provided": bool(guidance),
                **_trace_intent_summary(intents),
            }

        with langfuse_observation(
            "persona-generator",
            as_type="generation",
            model=_llm_model_name(self.llm),
            input=_generation_input({"system": PERSONA_GENERATOR_SYSTEM, "prompt": prompt}, trace_input),
            metadata={"agent": "persona_generator", "iteration": iteration, "mode": "REFINE" if is_refine else "GENERATE"},
            trace_id=trace_id,
            parent_span_id=parent_span_id,
        ) as generation:
            raw = await self.llm.generate(prompt, system_prompt=PERSONA_GENERATOR_SYSTEM)
            new_personas = self._parse(raw, intents)
            generation.update(
                output=_generation_output(raw, {"persona_count": len(new_personas)}),
                metadata={
                    "persona_count": len(new_personas),
                    "mode": "REFINE" if is_refine else "GENERATE",
                    "capture_io": capture_io_enabled(),
                },
            )

        if is_refine:
            merged = [p for p in existing_personas if (p.get("intent_num") or 0) not in pairs_to_regenerate]
            merged.extend(new_personas)
            personas = merged
            logger.info("PersonaGeneratorNode | REFINE merged | new=%d | kept=%d | total=%d",
                        len(new_personas), len(merged) - len(new_personas), len(personas))
        else:
            personas = new_personas
            logger.info("PersonaGeneratorNode parsed %d personas", len(personas))

        return {
            "iteration": iteration,
            "personas": personas,
            "pairs_to_regenerate": [],
            "history": state.get("history", []) + [
                {
                    "agent": "persona_generator",
                    "iteration": iteration,
                    "mode": "REFINE" if is_refine else "GENERATE",
                    "persona_count": len(personas),
                    "new_personas": len(new_personas),
                }
            ],
        }

    def _build_guidance(self, state: PersonaGraphState) -> str:
        parts = []
        base_guidance = state.get("guidance", "")
        if base_guidance:
            parts.append(f"Huong dan tu user/rule: {base_guidance}")

        revision_guidance = state.get("revision_guidance", "")
        if revision_guidance:
            parts.append(f"Phan hoi tu evaluator can sua: {revision_guidance}")

        return "\n".join(parts)

    def _build_prompt(self, intents: list[Intent], guidance: str, memory_context: str) -> str:
        intents_json = json.dumps(_intent_payload(intents), ensure_ascii=False, indent=2)
        memory_block = f"\n**Lich su / goi y truoc:**\n{memory_context}" if memory_context else ""
        guidance_block = f"\n{guidance}" if guidance else ""
        return PERSONA_GENERATOR_USER.format(
            intents_json=intents_json,
            guidance=guidance_block,
            memory_context=memory_block,
        )

    def _build_refine_prompt(
        self,
        failed_intents: list[Intent],
        critic_feedback: str,
        existing_personas: list[dict[str, Any]],
        pairs_to_regenerate: list[int],
        memory_context: str,
    ) -> str:
        intents_json = json.dumps(_intent_payload(failed_intents), ensure_ascii=False, indent=2)
        memory_block = f"\n**Lich su / goi y truoc:**\n{memory_context}" if memory_context else ""

        digest = self._build_passed_personas_digest(existing_personas, pairs_to_regenerate)
        feedback = critic_feedback or "Khong co feedback cu the. Review lai rubric va tao lai."

        return PERSONA_GENERATOR_REFINE_USER.format(
            intents_json=intents_json,
            critic_feedback=feedback,
            passed_personas_digest=digest,
            guidance="",
            memory_context=memory_block,
        )

    @staticmethod
    def _build_passed_personas_digest(
        personas: list[dict[str, Any]], pairs_to_regenerate: list[int]
    ) -> str:
        lines: list[str] = []
        for p in personas:
            inum = p.get("intent_num") or 0
            if inum in pairs_to_regenerate:
                continue
            pnum = p.get("persona_num", "?")
            ptype = p.get("persona_type", "")
            trigger = _str(p.get("trigger"))[:100]
            pain = _str(p.get("pain"))[:100]
            lines.append(
                f"- Intent {inum}, Persona {pnum}: type={ptype} | trigger={trigger} | pain={pain}"
            )
        return "\n".join(lines) if lines else "Khong co persona PASS."

    def _parse(self, raw: str, intents: list[Intent]) -> list[dict[str, Any]]:
        try:
            data = _loads_json(raw)
        except json.JSONDecodeError:
            logger.error("Persona generator returned invalid JSON | raw_preview=%s", raw[:300])
            return []

        items = data.get("personas", []) if isinstance(data, dict) else data if isinstance(data, list) else []
        if not isinstance(items, list):
            return []
        intent_map = {intent.intent_num or idx + 1: intent for idx, intent in enumerate(intents)}
        results: list[dict[str, Any]] = []

        for item in items:
            if not isinstance(item, dict):
                continue
            persona_type = item.get("persona_type", "")
            if not persona_type:
                continue

            inum = _coerce_int(item.get("intent_num", 0))
            intent = intent_map.get(inum)
            intent_id = intent.id if intent else (intents[0].id if intents else "")
            trait = "easy" if "happy" in persona_type.lower() else "hard"
            trigger = _str(item.get("trigger"))
            pain = _str(item.get("pain"))

            results.append(
                Persona(
                    intent_id=intent_id,
                    intent_num=inum,
                    intent_name=_str(item.get("intent_name")),
                    persona_num=item.get("persona_num", 0),
                    persona_type=persona_type,
                    trigger=trigger,
                    utterance=_str(item.get("utterance")),
                    frequency=_str(item.get("frequency")),
                    pain=pain,
                    reject=_str(item.get("reject")),
                    special_situation=_str(item.get("special_situation")),
                    research_source=_str(item.get("research_source")),
                    why_different=_str(item.get("why_different")),
                    expected_behavior=_str(item.get("expected_behavior")),
                    ai_response_example=_str(item.get("ai_response_example")),
                    name=f"{'Happy-path' if trait == 'easy' else 'Edge-case'} - {_str(item.get('intent_name'))}",
                    description=f"Trigger: {trigger} | Pain: {pain}",
                    trait_type=trait,
                ).model_dump()
            )

        return results


class PersonaEvaluatorNode:
    def __init__(self, llm: LLMClient, pass_threshold: float = 0.75):
        self.llm = llm
        self.pass_threshold = pass_threshold

    async def run(self, state: PersonaGraphState) -> dict[str, Any]:
        intents = state.get("intents", [])
        personas = state.get("personas", [])
        trace_id = state.get("trace_id") or None
        parent_span_id = state.get("parent_span_id") or None
        iteration = state.get("iteration", 0)
        max_iterations = state.get("max_iterations", 5)

        previous_evaluation = state.get("evaluation", {})
        previous_failed = previous_evaluation.get("pairs_to_regenerate", [])

        if previous_failed:
            regen_personas = [p for p in personas if (p.get("intent_num") or 0) in previous_failed]
            passed_personas = [p for p in personas if (p.get("intent_num") or 0) not in previous_failed]
            regen_intents = [i for i in intents if (i.intent_num or 0) in previous_failed]
            logger.info(
                "PersonaEvaluatorNode | RE-EVAL only regen pairs | regen=%d | passed=%d | previous_failed=%s",
                len(regen_personas), len(passed_personas), previous_failed,
            )
            evaluation = await self._evaluate_with_llm(
                regen_intents, regen_personas, trace_id, parent_span_id,
                iteration, max_iterations, passed_personas=passed_personas,
            )
        else:
            logger.info(
                "PersonaEvaluatorNode | FULL eval | personas=%d | trace_id=%s | parent_span_id=%s",
                len(personas), trace_id, parent_span_id,
            )
            evaluation = await self._evaluate_with_llm(
                intents, personas, trace_id, parent_span_id, iteration, max_iterations,
            )

        return {
            "evaluation": evaluation,
            "revision_guidance": evaluation.get("revision_guidance", ""),
            "pairs_to_regenerate": evaluation.get("pairs_to_regenerate", []),
            "history": state.get("history", []) + [
                {
                    "agent": "persona_evaluator",
                    "iteration": state.get("iteration", 0),
                    "approved": evaluation.get("approved", False),
                    "score": evaluation.get("score", 0.0),
                    "pairs_to_regenerate": evaluation.get("pairs_to_regenerate", []),
                    "issues": evaluation.get("issues", []),
                }
            ],
        }

    async def _evaluate_with_llm(
        self,
        intents: list[Intent],
        personas: list[dict[str, Any]],
        trace_id: str | None = None,
        parent_span_id: str | None = None,
        iteration: int = 0,
        max_iterations: int = 5,
        passed_personas: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if passed_personas:
            passed_context = (
                "\n**Personas da PASS (chi dung cho P5 cross-pair check, KHONG danh gia lai P1-P4):**\n"
                + json.dumps(passed_personas, ensure_ascii=False, indent=2)
            )
        else:
            passed_context = ""
        prompt = PERSONA_EVALUATOR_USER.format(
            intents_json=json.dumps(_intent_payload(intents), ensure_ascii=False, indent=2),
            personas_json=json.dumps(personas, ensure_ascii=False, indent=2),
            passed_context=passed_context,
            iteration_number=iteration,
            max_iterations=max_iterations,
        )
        trace_input = {
            "agent": "persona_evaluator",
            "persona_count": len(personas),
            **_trace_intent_summary(intents),
        }
        with langfuse_observation(
            "persona-evaluator",
            as_type="generation",
            model=_llm_model_name(self.llm),
            input=_generation_input({"system": PERSONA_EVALUATOR_SYSTEM, "prompt": prompt}, trace_input),
            metadata={"agent": "persona_evaluator", "pass_threshold": self.pass_threshold},
            trace_id=trace_id,
            parent_span_id=parent_span_id,
        ) as generation:
            raw = await self.llm.generate(prompt, system_prompt=PERSONA_EVALUATOR_SYSTEM)
            try:
                data = _loads_json(raw)
            except json.JSONDecodeError:
                logger.error("Persona evaluator returned invalid JSON | raw_preview=%s", raw[:300])
                result = {
                    "approved": False,
                    "score": 0.0,
                    "pairs_to_regenerate": [i.intent_num for i in intents],
                    "pair_results": [],
                    "issues": [{"severity": "high", "message": "Evaluator returned invalid JSON"}],
                    "revision_guidance": "Tra ve dung JSON schema va danh gia lai batch personas.",
                }
                generation.update(
                    output=_generation_output(None, {"approved": False, "error": "invalid_json"}),
                    metadata={"approved": False, "error": "invalid_json", "capture_io": capture_io_enabled()},
                )
                return result
            if not isinstance(data, dict):
                result = {
                    "approved": False,
                    "score": 0.0,
                    "pairs_to_regenerate": [i.intent_num for i in intents],
                    "pair_results": [],
                    "issues": [{"severity": "high", "message": "Evaluator JSON must be an object"}],
                    "revision_guidance": "Tra ve mot JSON object dung schema danh gia.",
                }
                generation.update(
                    output=_generation_output(None, {"approved": False, "error": "not_dict"}),
                    metadata={"approved": False, "error": "not_dict", "capture_io": capture_io_enabled()},
                )
                return result

            pairs_to_regenerate = data.get("pairs_to_regenerate", [])
            if not isinstance(pairs_to_regenerate, list):
                pairs_to_regenerate = []
            pairs_to_regenerate = [_coerce_int(p) for p in pairs_to_regenerate]

            batch_summary = data.get("batch_summary", {})
            if not isinstance(batch_summary, dict):
                batch_summary = {}
            pair_results = data.get("pair_results", [])
            if not isinstance(pair_results, list):
                pair_results = []

            total_pairs = _coerce_int(batch_summary.get("total_pairs"), len(pair_results))
            pairs_passed = _coerce_int(batch_summary.get("pairs_passed"), 0)
            score = (pairs_passed / total_pairs) if total_pairs > 0 else 0.0
            score = max(0.0, min(score, 1.0))

            approved = len(pairs_to_regenerate) == 0

            logger.info(
                "PersonaEvaluatorNode | verdict=%s | approved=%s | pairs_to_regenerate=%s | score=%.2f | pairs_passed=%d/%d",
                "Pass" if approved else "Revision",
                approved,
                pairs_to_regenerate,
                score,
                pairs_passed,
                total_pairs,
            )

            fixes: list[str] = []
            all_issues: list[dict[str, Any]] = []
            for pr in pair_results:
                if not isinstance(pr, dict):
                    continue
                pr_verdict = str(pr.get("verdict", "")).upper()
                if pr_verdict == "FAIL":
                    pr_fixes = pr.get("fixes", [])
                    if isinstance(pr_fixes, list):
                        fixes.extend(str(f) for f in pr_fixes if f)
                    pr_issues = pr.get("persona_issues", {})
                    if isinstance(pr_issues, dict):
                        for pid, msgs in pr_issues.items():
                            if isinstance(msgs, list):
                                for msg in msgs:
                                    all_issues.append({"persona_id": pid, "message": str(msg)})

            revision_guidance = "\n".join(fixes) if fixes else _revision_guidance_from(data)

            result = {
                "approved": approved,
                "score": score,
                "verdict": "Pass" if approved else "Revision",
                "pairs_to_regenerate": pairs_to_regenerate,
                "pair_results": pair_results,
                "batch_summary": batch_summary,
                "issues": all_issues,
                "top_fixes": fixes,
                "revision_guidance": revision_guidance,
            }
            generation.update(
                output=_generation_output(data, {
                    "approved": result["approved"],
                    "score": result["score"],
                    "verdict": result["verdict"],
                    "pairs_to_regenerate": pairs_to_regenerate,
                    "pairs_passed": pairs_passed,
                    "total_pairs": total_pairs,
                }),
                metadata={
                    "approved": result["approved"],
                    "score": result["score"],
                    "verdict": result["verdict"],
                    "pairs_to_regenerate": pairs_to_regenerate,
                    "capture_io": capture_io_enabled(),
                },
            )
            return result


class PersonaOrchestratorNode:
    def run(self, state: PersonaGraphState) -> dict[str, Any]:
        personas = state.get("personas", [])
        evaluation = state.get("evaluation", {})
        iteration = state.get("iteration", 0)
        max_iterations = state.get("max_iterations", 5)
        trace_id = state.get("trace_id") or None
        parent_span_id = state.get("parent_span_id") or None
        pairs_to_regenerate = evaluation.get("pairs_to_regenerate", [])

        logger.info(
            "PersonaOrchestratorNode | state keys=%s | trace_id=%s | parent_span_id=%s",
            list(state.keys()),
            trace_id,
            parent_span_id,
        )
        if not personas:
            next_node = "persona_generator"
            reason = "No personas generated yet."
        elif not pairs_to_regenerate:
            next_node = "end"
            reason = "All pairs passed evaluation."
        elif iteration >= max_iterations:
            next_node = "end"
            reason = f"Reached max iterations ({max_iterations}); returning best available personas. Unresolved: {pairs_to_regenerate}"
        else:
            next_node = "persona_generator"
            reason = f"{len(pairs_to_regenerate)} pairs need regeneration: {pairs_to_regenerate}"

        logger.info("PersonaOrchestratorNode | next=%s | reason=%s", next_node, reason)
        with langfuse_observation(
            "persona-orchestrator",
            as_type="span",
            input={
                "iteration": iteration,
                "persona_count": len(personas),
                "approved": evaluation.get("approved", False),
                "pairs_to_regenerate": pairs_to_regenerate,
            },
            metadata={"agent": "orchestrator"},
            trace_id=trace_id,
            parent_span_id=parent_span_id,
        ) as span:
            span.update(output={"next_node": next_node, "reason": reason})

        return {
            "next_node": next_node,
            "pairs_to_regenerate": pairs_to_regenerate,
            "history": state.get("history", []) + [
                {
                    "agent": "orchestrator",
                    "iteration": iteration,
                    "next_node": next_node,
                    "reason": reason,
                    "pairs_to_regenerate": pairs_to_regenerate,
                }
            ],
        }


class PersonaGenerationGraph:
    def __init__(
        self,
        llm: LLMClient,
        max_iterations: int = 5,
        pass_threshold: float = 0.75,
    ):
        self.llm = llm
        self.max_iterations = max_iterations
        self.pass_threshold = pass_threshold
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(PersonaGraphState)
        workflow.add_node("orchestrator", PersonaOrchestratorNode().run)
        workflow.add_node("persona_generator", PersonaGeneratorNode(self.llm).run)
        workflow.add_node("persona_evaluator", PersonaEvaluatorNode(self.llm, self.pass_threshold).run)

        workflow.add_edge(START, "orchestrator")
        workflow.add_conditional_edges(
            "orchestrator",
            self._route_from_orchestrator,
            ["persona_generator", END],
        )
        workflow.add_edge("persona_generator", "persona_evaluator")
        workflow.add_edge("persona_evaluator", "orchestrator")
        return workflow.compile()

    def _route_from_orchestrator(self, state: PersonaGraphState) -> Literal["persona_generator", "__end__"]:
        if state.get("next_node") == "persona_generator":
            return "persona_generator"
        return END

    async def run(
        self,
        intents: list[Intent],
        guidance: str = "",
        memory_context: str = "",
        trace_id: str | None = None,
    ) -> PersonaGraphState:
        initial_state: PersonaGraphState = {
            "intents": intents,
            "guidance": guidance,
            "memory_context": memory_context,
            "iteration": 0,
            "max_iterations": self.max_iterations,
            "personas": [],
            "evaluation": {},
            "revision_guidance": "",
            "pairs_to_regenerate": [],
            "history": [],
            "trace_id": trace_id or "",
            "parent_span_id": "",
        }
        with langfuse_observation(
            "persona-generation-graph",
            as_type="span",
            input={
                **_trace_intent_summary(intents),
                "guidance_provided": bool(guidance),
            },
            metadata={
                "stage": "persona_generation",
                "agent_architecture": "langgraph_multi_agent",
                "max_iterations": self.max_iterations,
                "pass_threshold": self.pass_threshold,
            },
            trace_id=trace_id,
        ) as root_span:
            initial_state["parent_span_id"] = root_span.id
            logger.info(
                "PersonaGenerationGraph | root_span.id=%s | root_span.trace_id=%s | type=%s | parent_span_id in state=%s",
                root_span.id,
                getattr(root_span, "trace_id", "N/A"),
                type(root_span).__name__,
                initial_state["parent_span_id"],
            )
            final_state = await self.graph.ainvoke(initial_state)
            evaluation = final_state.get("evaluation", {})
            root_span.update(
                output={
                    "persona_count": len(final_state.get("personas", [])),
                    "iterations": final_state.get("iteration", 0),
                    "approved": evaluation.get("approved", False),
                    "score": evaluation.get("score"),
                    "verdict": evaluation.get("verdict"),
                    "pairs_to_regenerate": evaluation.get("pairs_to_regenerate", []),
                }
            )
            return final_state
