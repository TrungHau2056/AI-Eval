from __future__ import annotations

import json
import logging
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from src.llm.base import LLMClient
from src.models.schemas import Intent, Persona
from src.observability.langfuse import capture_io_enabled, langfuse_observation

logger = logging.getLogger(__name__)


GENERATOR_SYSTEM_PROMPT = """# ROLE
Ban la mot Senior UX Researcher chuyen nghiep. Nhiem vu cua ban la nhan vao MOT DANH SACH Intents va voi moi Intent, xay dung dung 2 Persona co hanh vi va tam ly doi lap nhau de phuc vu tao bo kich ban kiem thu.

# QUY TAC BAT BUOC
1. Voi N intents dau vao, bat buoc tra ve dung 2 * N personas.
2. Moi intent phai co 1 persona happy-path va 1 persona edge-case.
3. Persona phai dua tren hanh vi, khong dua vao nhan khau hoc chung chung.
4. Moi persona phai co trigger, utterance, frequency, pain, reject, expected_behavior.
5. Hai persona trong cung intent phai khac nhau ro ve trigger, giong dieu utterance, pain/reject.
6. Tra ve JSON hop le, khong them markdown hay text ben ngoai JSON."""

GENERATOR_USER_PROMPT = """Xay dung 2 Persona doi lap cho danh sach Intents sau:

**Danh sach Intents:**
{intents_json}

{guidance}
{memory_context}

Tra ve JSON dung schema:
{{
  "personas": [
    {{
      "intent_num": 1,
      "intent_name": "Ten intent ke thua tu input",
      "persona_num": 1,
      "persona_type": "happy-path",
      "trigger": "Hoan canh kich hoat cu the",
      "utterance": "Cau chat mau cua user",
      "frequency": "Tan suat cu the kem moc thoi gian",
      "pain": "Vuong mac thuc te",
      "reject": "Doi tuong/giai phap persona tu choi + ly do",
      "special_situation": "Tinh huong dac biet neu co",
      "research_source": "Nguon gia dinh/gia dinh tu data neu co",
      "why_different": "Vi sao persona nay khac persona con lai",
      "expected_behavior": "Hanh vi AI ky vong",
      "ai_response_example": "Vi du ngan cach AI nen phan hoi"
    }}
  ]
}}"""

EVALUATOR_SYSTEM_PROMPT = """# ROLE
Ban la Persona Quality Evaluator trong mot he thong multi-agent. Nhiem vu cua ban la cham batch personas theo Persona Research Rubric v0.2 truoc khi cho phep tao test case.

# HARD GATE
Neu sai bat ky gate nao thi approved=false, verdict="Revision", va viet revision_guidance cu the:
1. Pool persona unique phai >= 3.
2. Moi intent phai co >= 2 persona.
3. Moi persona phai co research_source.
4. Moi persona phai co day du cot bat buoc: trigger, utterance, frequency, pain, reject.

# SCORING RUBRIC
Cham 4 tieu chi, moi tieu chi muc 1-4:
- P1 Behavioral Specificity / Persona du chi tiet, weight 3x. Check trigger, utterance, frequency, pain. 4/4 cu the => 4; 3/4 => 3; 2/4 => 2; <=1/4 => 1.
- P2 Inter-Persona Divergence / 2 persona du khac nhau, weight 2x. Voi moi intent, 2 persona phai khac >=3/5 khia canh va BAT BUOC khac trigger + utterance register. 9-10/10 intent pass => 4; 7-8 => 3; 5-6 => 2; <5 => 1. Neu input it hon 10 intent, scale theo ty le intent pass.
- P3 Internal Consistency / Persona khong tu mau thuan, weight 1x. Chi cham khi P1 >= 3; neu P1 < 3 thi P3=0. Check trigger-frequency, trigger-pain, trigger-utterance, frequency-pain, frequency-utterance, pain-utterance.
- P4 Falsifiable Reject / Persona co bien gioi ro, weight 1x. Reject phai co doi tuong cu the va tie voi hoan canh persona. 100% pass => 4; >=75% => 3; >=50% cu the nhung thieu tie => 2; <50% hoac co reject trong => 1.

Tong diem = P1*3 + P2*2 + P3 + P4. Max=28. Pass neu >=75% (>=21/28), Revision neu 50-74%, Rewrite neu <50%.

# HARD FAIL CAPS
- P1=1 => percent toi da 40%.
- P2=1 => percent toi da 40%.
- P4=1 => percent toi da 60%.

Tra ve JSON hop le, khong them markdown hay text ben ngoai JSON."""

EVALUATOR_USER_PROMPT = """Danh gia batch personas sau:

**Intents goc:**
{intents_json}

**Personas can danh gia:**
{personas_json}

Hay tra ve JSON dung schema:
{{
  "approved": true,
  "verdict": "Pass|Revision|Rewrite",
  "total_score": 21,
  "max_score": 28,
  "percent": 0.75,
  "criteria": {{
    "P1": {{"level": 4, "weighted_score": 12, "reason": "Ly do ngan gon"}},
    "P2": {{"level": 4, "weighted_score": 8, "reason": "Ly do ngan gon"}},
    "P3": {{"level": 3, "weighted_score": 3, "reason": "Ly do ngan gon"}},
    "P4": {{"level": 4, "weighted_score": 4, "reason": "Ly do ngan gon"}}
  }},
  "issues": [
    {{
      "severity": "low|medium|high",
      "message": "Mo ta van de cu the",
      "intent_num": 1
    }}
  ],
  "top_fixes": [
    "P[#] (diem/4) - gap cu the - viec can sua"
  ],
  "revision_guidance": "Huong dan ngan gon de persona_generator sua neu approved=false"
}}"""


class PersonaGraphState(TypedDict, total=False):
    intents: list[Intent]
    guidance: str
    memory_context: str
    iteration: int
    max_iterations: int
    personas: list[dict[str, Any]]
    evaluation: dict[str, Any]
    revision_guidance: str
    next_node: str
    history: list[dict[str, Any]]


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


def _coerce_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    if score > 1.0:
        score = score / 100.0
    return max(0.0, min(score, 1.0))


def _score_from_evaluation(data: dict[str, Any]) -> float:
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

    fixes = data.get("top_fixes", [])
    if isinstance(fixes, list):
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
        guidance = self._build_guidance(state)
        prompt = self._build_prompt(intents, guidance, state.get("memory_context", ""))

        logger.info("PersonaGeneratorNode | iteration=%d | intents=%d", iteration, len(intents))
        trace_input = {
            "agent": "persona_generator",
            "iteration": iteration,
            "guidance_provided": bool(guidance),
            **_trace_intent_summary(intents),
        }
        with langfuse_observation(
            "persona-generator",
            as_type="generation",
            model=_llm_model_name(self.llm),
            input=_generation_input({"system": GENERATOR_SYSTEM_PROMPT, "prompt": prompt}, trace_input),
            metadata={"agent": "persona_generator", "iteration": iteration},
        ) as generation:
            raw = await self.llm.generate(prompt, system_prompt=GENERATOR_SYSTEM_PROMPT)
            personas = self._parse(raw, intents)
            generation.update(
                output=_generation_output(raw, {"persona_count": len(personas)}),
                metadata={
                    "persona_count": len(personas),
                    "capture_io": capture_io_enabled(),
                },
            )
        logger.info("PersonaGeneratorNode parsed %d personas", len(personas))

        return {
            "iteration": iteration,
            "personas": personas,
            "history": state.get("history", []) + [
                {
                    "agent": "persona_generator",
                    "iteration": iteration,
                    "persona_count": len(personas),
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
        return GENERATOR_USER_PROMPT.format(
            intents_json=intents_json,
            guidance=guidance_block,
            memory_context=memory_block,
        )

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
            trigger = item.get("trigger", "")
            pain = item.get("pain", "")

            results.append(
                Persona(
                    intent_id=intent_id,
                    intent_num=inum,
                    intent_name=item.get("intent_name", ""),
                    persona_num=item.get("persona_num", 0),
                    persona_type=persona_type,
                    trigger=trigger,
                    utterance=item.get("utterance", ""),
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
        structural_eval = self._validate_structure(intents, personas)

        logger.info("PersonaEvaluatorNode | personas=%d", len(personas))
        llm_eval = await self._evaluate_with_llm(intents, personas)
        evaluation = self._merge_evaluations(structural_eval, llm_eval)

        return {
            "evaluation": evaluation,
            "revision_guidance": evaluation.get("revision_guidance", ""),
            "history": state.get("history", []) + [
                {
                    "agent": "persona_evaluator",
                    "iteration": state.get("iteration", 0),
                    "approved": evaluation.get("approved", False),
                    "score": evaluation.get("score", 0.0),
                    "issues": evaluation.get("issues", []),
                }
            ],
        }

    async def _evaluate_with_llm(
        self, intents: list[Intent], personas: list[dict[str, Any]]
    ) -> dict[str, Any]:
        prompt = EVALUATOR_USER_PROMPT.format(
            intents_json=json.dumps(_intent_payload(intents), ensure_ascii=False, indent=2),
            personas_json=json.dumps(personas, ensure_ascii=False, indent=2),
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
            input=_generation_input({"system": EVALUATOR_SYSTEM_PROMPT, "prompt": prompt}, trace_input),
            metadata={"agent": "persona_evaluator", "pass_threshold": self.pass_threshold},
        ) as generation:
            raw = await self.llm.generate(prompt, system_prompt=EVALUATOR_SYSTEM_PROMPT)
            try:
                data = _loads_json(raw)
            except json.JSONDecodeError:
                logger.error("Persona evaluator returned invalid JSON | raw_preview=%s", raw[:300])
                result = {
                    "approved": False,
                    "score": 0.0,
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
                    "issues": [{"severity": "high", "message": "Evaluator JSON must be an object"}],
                    "revision_guidance": "Tra ve mot JSON object dung schema danh gia.",
                }
                generation.update(
                    output=_generation_output(None, {"approved": False, "error": "not_dict"}),
                    metadata={"approved": False, "error": "not_dict", "capture_io": capture_io_enabled()},
                )
                return result

            score = _score_from_evaluation(data)
            verdict = str(data.get("verdict", "")).lower()
            approved = bool(data.get("approved", False)) or verdict == "pass" or score >= self.pass_threshold
            result = {
                "approved": approved,
                "score": score,
                "verdict": data.get("verdict", "Pass" if approved else "Revision"),
                "criteria": data.get("criteria", {}),
                "issues": data.get("issues", []) if isinstance(data.get("issues", []), list) else [],
                "top_fixes": data.get("top_fixes", []) if isinstance(data.get("top_fixes", []), list) else [],
                "revision_guidance": _revision_guidance_from(data),
            }
            generation.update(
                output=_generation_output(data, {
                    "approved": result["approved"],
                    "score": result["score"],
                    "verdict": result["verdict"],
                    "issue_count": len(result["issues"]),
                }),
                metadata={
                    "approved": result["approved"],
                    "score": result["score"],
                    "verdict": result["verdict"],
                    "issue_count": len(result["issues"]),
                    "capture_io": capture_io_enabled(),
                },
            )
            return result

    def _validate_structure(
        self, intents: list[Intent], personas: list[dict[str, Any]]
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []
        expected_count = len(intents) * 2
        if len(personas) < expected_count:
            issues.append(
                {
                    "severity": "high",
                    "message": f"Expected at least {expected_count} personas for {len(intents)} intents, got {len(personas)}.",
                }
            )
        if len(personas) < 3:
            issues.append(
                {
                    "severity": "high",
                    "message": "Persona pool must contain at least 3 unique personas before test case writing.",
                }
            )

        for intent in intents:
            matching = [p for p in personas if p.get("intent_id") == intent.id]
            if len(matching) < 2:
                issues.append(
                    {
                        "severity": "high",
                        "intent_num": intent.intent_num,
                        "message": "Intent must have at least 2 personas.",
                    }
                )

        required_fields = ("trigger", "utterance", "frequency", "pain", "reject")
        for persona in personas:
            missing = [field for field in required_fields if not str(persona.get(field, "")).strip()]
            if missing:
                issues.append(
                    {
                        "severity": "high",
                        "message": f"Persona {persona.get('id', '')} is missing required fields: {', '.join(missing)}.",
                    }
                )
            if not str(persona.get("research_source", "")).strip():
                issues.append(
                    {
                        "severity": "high",
                        "message": f"Persona {persona.get('id', '')} is missing research_source.",
                    }
                )

        return {
            "approved": not issues,
            "score": 1.0 if not issues else 0.0,
            "issues": issues,
            "revision_guidance": "Sua hard gate: pool >=3, moi intent >=2 persona, moi persona co research_source va du trigger/utterance/frequency/pain/reject."
            if issues
            else "",
        }

    def _merge_evaluations(
        self, structural_eval: dict[str, Any], llm_eval: dict[str, Any]
    ) -> dict[str, Any]:
        issues = structural_eval.get("issues", []) + llm_eval.get("issues", [])
        score = min(_coerce_score(structural_eval.get("score")), _coerce_score(llm_eval.get("score")))
        approved = (
            structural_eval.get("approved", False)
            and llm_eval.get("approved", False)
            and score >= self.pass_threshold
        )

        revision_parts = [
            structural_eval.get("revision_guidance", ""),
            llm_eval.get("revision_guidance", ""),
        ]
        revision_guidance = "\n".join(p for p in revision_parts if p).strip()
        if not approved and not revision_guidance:
            revision_guidance = "Lam persona cu the hon, doi lap hon va bam sat tung intent hon."

        return {
            "approved": approved,
            "score": score,
            "verdict": llm_eval.get("verdict", "Pass" if approved else "Revision"),
            "criteria": llm_eval.get("criteria", {}),
            "issues": issues,
            "top_fixes": llm_eval.get("top_fixes", []),
            "revision_guidance": revision_guidance,
        }


class PersonaOrchestratorNode:
    def run(self, state: PersonaGraphState) -> dict[str, Any]:
        personas = state.get("personas", [])
        evaluation = state.get("evaluation", {})
        iteration = state.get("iteration", 0)
        max_iterations = state.get("max_iterations", 3)

        if not personas:
            next_node = "persona_generator"
            reason = "No personas generated yet."
        elif evaluation.get("approved", False):
            next_node = "end"
            reason = "Evaluator approved personas."
        elif iteration >= max_iterations:
            next_node = "end"
            reason = "Reached max iterations; returning best available personas."
        else:
            next_node = "persona_generator"
            reason = "Evaluator requested revisions."

        logger.info("PersonaOrchestratorNode | next=%s | reason=%s", next_node, reason)
        with langfuse_observation(
            "persona-orchestrator",
            as_type="span",
            input={
                "iteration": iteration,
                "persona_count": len(personas),
                "approved": evaluation.get("approved", False),
            },
            metadata={"agent": "orchestrator"},
        ) as span:
            span.update(output={"next_node": next_node, "reason": reason})

        return {
            "next_node": next_node,
            "history": state.get("history", []) + [
                {
                    "agent": "orchestrator",
                    "iteration": iteration,
                    "next_node": next_node,
                    "reason": reason,
                }
            ],
        }


class PersonaGenerationGraph:
    def __init__(
        self,
        llm: LLMClient,
        max_iterations: int = 3,
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
            "history": [],
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
        ) as root_span:
            final_state = await self.graph.ainvoke(initial_state)
            evaluation = final_state.get("evaluation", {})
            root_span.update(
                output={
                    "persona_count": len(final_state.get("personas", [])),
                    "iterations": final_state.get("iteration", 0),
                    "approved": evaluation.get("approved", False),
                    "score": evaluation.get("score"),
                    "verdict": evaluation.get("verdict"),
                }
            )
            return final_state
