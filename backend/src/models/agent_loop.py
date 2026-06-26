"""
Persona Agent Loop
==================
Core agent loop cho việc xây dựng persona chất lượng cao.

Flow cho mỗi intent:
  1. Generate 2 persona (easy + hard) từ intent + evidence
  2. Evaluate từng persona theo rubric
  3. Nếu chưa pass → Improve persona dựa trên feedback
  4. Lặp lại tối đa max_iterations lần
  5. Trả về persona tốt nhất đạt được

Design decisions:
  - Tách biệt generate/evaluate/improve thành 3 LLM call riêng biệt
    (thay vì 1 call lớn) để dễ debug và kiểm soát từng bước
  - Lưu toàn bộ history để researcher có thể review quá trình
  - Graceful fallback: nếu hết iteration vẫn trả về persona tốt nhất
"""
import json
import logging
from typing import Callable

from ..llm.base import PersonaAgentLLMBase
from ..schemas.models import (
    AgentLoopResult,
    AgentLoopState,
    CriterionScore,
    IntentInput,
    PersonaDraft,
    PersonaEvaluation,
    RubricInput,
)
from ..prompts.templates import (
    PERSONA_BUILDER_SYSTEM_PROMPT,
    PERSONA_EVALUATOR_SYSTEM_PROMPT,
    PERSONA_IMPROVER_SYSTEM_PROMPT,
    PERSONA_GENERATION_PROMPT,
    PERSONA_EVALUATION_PROMPT,
    PERSONA_IMPROVEMENT_PROMPT,
    format_rubric_for_prompt,
)

logger = logging.getLogger(__name__)


class PersonaAgentLoop:
    """
    Agent loop sinh và cải thiện persona theo rubric.

    Usage:
        loop = PersonaAgentLoop(llm=client, max_iterations=5)
        result = await loop.run(intent, rubric)
    """

    def __init__(
        self,
        llm: PersonaAgentLLMBase,
        max_iterations: int = 5,
        on_progress: Callable[[str], None] | None = None,
    ):
        self.llm = llm
        self.max_iterations = max_iterations
        self.on_progress = on_progress or (lambda msg: None)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def run(
        self,
        intent: IntentInput,
        rubric: RubricInput,
        guidance: str = "",
    ) -> AgentLoopResult:
        """
        Chạy agent loop cho 1 intent.

        Returns:
            AgentLoopResult với persona tốt nhất và lịch sử evaluation
        """
        state = AgentLoopState(
            intent=intent,
            rubric=rubric,
            max_iterations=self.max_iterations,
        )

        self._log(f"🚀 Bắt đầu agent loop cho intent: '{intent.goal}'")

        # ---- Iteration 0: Initial generation ----
        state.iteration = 1
        self._log(f"  📝 Iteration {state.iteration}/{self.max_iterations}: Generating personas...")

        try:
            personas = await self._generate_personas(intent, rubric, guidance)
        except Exception as e:
            logger.error(f"Failed to generate initial personas: {e}")
            return AgentLoopResult(
                intent_id=intent.id,
                intent_goal=intent.goal,
                passed=False,
                failure_reason=f"Initial generation failed: {e}",
                total_iterations=0,
            )

        state.current_drafts = personas
        state.history.append({
            "iteration": state.iteration,
            "event": "initial_generation",
            "personas": [p.model_dump() for p in personas],
        })

        # ---- Evaluate + improve loop ----
        while state.iteration <= self.max_iterations:
            self._log(f"  🔍 Iteration {state.iteration}: Evaluating {len(state.current_drafts)} personas...")

            evaluations = []
            for persona in state.current_drafts:
                eval_result = await self._evaluate_persona(persona, intent, rubric, state.iteration)
                evaluations.append(eval_result)
                self._log(
                    f"     Persona '{persona.name}' ({persona.trait_type}): "
                    f"{eval_result.normalized_score:.0%} {'✅' if eval_result.passed else '❌'}"
                )

            state.evaluations = evaluations
            state.history.append({
                "iteration": state.iteration,
                "event": "evaluation",
                "evaluations": [e.model_dump() for e in evaluations],
            })

            # Check if all personas passed
            all_passed = all(e.passed for e in evaluations)
            if all_passed:
                state.passed = True
                self._log(f"  ✅ Tất cả personas đạt yêu cầu sau iteration {state.iteration}!")
                break

            # Max iterations reached — stop
            if state.iteration >= self.max_iterations:
                self._log(
                    f"  ⚠️  Hết {self.max_iterations} iteration. "
                    f"Trả về persona tốt nhất đạt được."
                )
                break

            # ---- Improve failed personas ----
            state.iteration += 1
            self._log(f"  🔧 Iteration {state.iteration}: Improving failed personas...")

            improved = []
            for persona, evaluation in zip(state.current_drafts, evaluations):
                if evaluation.passed:
                    improved.append(persona)  # Keep passing persona unchanged
                    self._log(f"     ✓ '{persona.name}' đã pass, giữ nguyên.")
                else:
                    try:
                        new_persona = await self._improve_persona(
                            persona, evaluation, intent, state.iteration
                        )
                        improved.append(new_persona)
                        self._log(f"     🔄 '{persona.name}' → cải thiện thành '{new_persona.name}'")
                    except Exception as e:
                        logger.warning(f"Failed to improve persona '{persona.name}': {e}")
                        improved.append(persona)  # Keep original on error

            state.current_drafts = improved
            state.history.append({
                "iteration": state.iteration,
                "event": "improvement",
                "personas": [p.model_dump() for p in improved],
            })

        return AgentLoopResult(
            intent_id=intent.id,
            intent_goal=intent.goal,
            final_personas=state.current_drafts,
            final_evaluations=state.evaluations,
            total_iterations=state.iteration,
            passed=state.passed,
            failure_reason="" if state.passed else (
                f"Không đạt ngưỡng {rubric.pass_threshold:.0%} "
                f"sau {state.iteration} iteration"
            ),
        )

    # ------------------------------------------------------------------
    # Step 1: Generate personas
    # ------------------------------------------------------------------

    async def _generate_personas(
        self,
        intent: IntentInput,
        rubric: RubricInput,
        guidance: str = "",
    ) -> list[PersonaDraft]:
        evidence_text = (
            "\n".join(f"  - {e}" for e in intent.evidence)
            if intent.evidence
            else "  (Không có evidence cụ thể)"
        )

        prompt = PERSONA_GENERATION_PROMPT.format(
            context=intent.context,
            goal=intent.goal,
            evidence=evidence_text,
            guidance=f"\n**Hướng dẫn thêm từ researcher:** {guidance}" if guidance else "",
        )

        raw = await self.llm.generate(prompt, system_prompt=PERSONA_BUILDER_SYSTEM_PROMPT)
        return self._parse_personas(raw, intent.id)

    def _parse_personas(self, raw: str, intent_id: str) -> list[PersonaDraft]:
        """Parse LLM response thành list PersonaDraft."""
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]
        try:
            data = json.loads(text.strip())
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in persona generation: {e}\nRaw: {raw[:500]}")
            raise ValueError(f"LLM trả về JSON không hợp lệ: {e}")

        items = data.get("personas", data if isinstance(data, list) else [])
        personas = []
        for item in items:
            if not item.get("name") or not item.get("description"):
                continue
            personas.append(
                PersonaDraft(
                    intent_id=intent_id,
                    name=item.get("name", ""),
                    description=item.get("description", ""),
                    trait_type=item.get("trait_type", "easy"),
                    background=item.get("background", ""),
                    pain_points=item.get("pain_points", []),
                    communication_style=item.get("communication_style", ""),
                    sample_utterances=item.get("sample_utterances", []),
                    reject_conditions=item.get("reject_conditions", []),
                )
            )
        return personas

    # ------------------------------------------------------------------
    # Step 2: Evaluate persona
    # ------------------------------------------------------------------

    async def _evaluate_persona(
        self,
        persona: PersonaDraft,
        intent: IntentInput,
        rubric: RubricInput,
        iteration: int,
    ) -> PersonaEvaluation:
        evidence_text = (
            "\n".join(f"  - {e}" for e in intent.evidence)
            if intent.evidence
            else "  (Không có evidence cụ thể)"
        )
        persona_json = json.dumps(persona.model_dump(), ensure_ascii=False, indent=2)

        prompt = PERSONA_EVALUATION_PROMPT.format(
            context=intent.context,
            goal=intent.goal,
            evidence=evidence_text,
            persona_json=persona_json,
            rubric_text=format_rubric_for_prompt(rubric),
        )

        raw = await self.llm.generate(prompt, system_prompt=PERSONA_EVALUATOR_SYSTEM_PROMPT)
        return self._parse_evaluation(raw, persona.id, rubric, iteration)

    def _parse_evaluation(
        self,
        raw: str,
        persona_id: str,
        rubric: RubricInput,
        iteration: int,
    ) -> PersonaEvaluation:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]

        try:
            data = json.loads(text.strip())
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in evaluation: {e}\nRaw: {raw[:500]}")
            # Graceful fallback: trả về evaluation với điểm 0
            return PersonaEvaluation(
                persona_id=persona_id,
                overall_feedback=f"Parse error: {e}",
                iteration=iteration,
            )

        criterion_map = {c.id: c for c in rubric.criteria}
        scores = []
        weighted_total = 0.0
        weighted_max = 0.0

        for cs_data in data.get("criterion_scores", []):
            crit_id = cs_data.get("criterion_id", "")
            crit = criterion_map.get(crit_id)
            if not crit:
                # Tìm theo name fallback
                crit = next(
                    (c for c in rubric.criteria if c.name == cs_data.get("criterion_name")),
                    None,
                )

            max_s = crit.max_score if crit else cs_data.get("max_score", 3)
            weight = crit.weight if crit else 1.0
            score_val = min(int(cs_data.get("score", 0)), max_s)

            cs = CriterionScore(
                criterion_id=crit_id or cs_data.get("criterion_name", ""),
                criterion_name=cs_data.get("criterion_name", crit_id),
                score=score_val,
                max_score=max_s,
                reasoning=cs_data.get("reasoning", ""),
                improvement_suggestions=cs_data.get("improvement_suggestions", []),
            )
            scores.append(cs)
            weighted_total += score_val * weight
            weighted_max += max_s * weight

        normalized = weighted_total / weighted_max if weighted_max > 0 else 0.0
        passed = normalized >= rubric.pass_threshold

        return PersonaEvaluation(
            persona_id=persona_id,
            criterion_scores=scores,
            total_score=weighted_total,
            max_possible=weighted_max,
            normalized_score=normalized,
            passed=passed,
            overall_feedback=data.get("overall_feedback", ""),
            iteration=iteration,
        )

    # ------------------------------------------------------------------
    # Step 3: Improve persona
    # ------------------------------------------------------------------

    async def _improve_persona(
        self,
        persona: PersonaDraft,
        evaluation: PersonaEvaluation,
        intent: IntentInput,
        iteration: int,
    ) -> PersonaDraft:
        evidence_text = (
            "\n".join(f"  - {e}" for e in intent.evidence)
            if intent.evidence
            else "  (Không có evidence cụ thể)"
        )
        persona_json = json.dumps(persona.model_dump(), ensure_ascii=False, indent=2)

        # Tổng hợp feedback điểm thấp
        low_scores = [
            cs for cs in evaluation.criterion_scores
            if cs.score < cs.max_score
        ]
        low_score_text = "\n".join(
            f"- [{cs.criterion_name}] ({cs.score}/{cs.max_score}): "
            + "; ".join(cs.improvement_suggestions)
            for cs in low_scores
        ) or "Không có điểm cụ thể nào thấp."

        prompt = PERSONA_IMPROVEMENT_PROMPT.format(
            context=intent.context,
            goal=intent.goal,
            evidence=evidence_text,
            persona_json=persona_json,
            iteration=iteration - 1,
            feedback_text=evaluation.overall_feedback,
            low_score_details=low_score_text,
            trait_type=persona.trait_type,
        )

        raw = await self.llm.generate(prompt, system_prompt=PERSONA_IMPROVER_SYSTEM_PROMPT)
        return self._parse_single_persona(raw, persona.intent_id, persona.trait_type)

    def _parse_single_persona(
        self, raw: str, intent_id: str, trait_type: str
    ) -> PersonaDraft:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]

        try:
            item = json.loads(text.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON parse error in improvement: {e}")

        return PersonaDraft(
            intent_id=intent_id,
            name=item.get("name", "Improved Persona"),
            description=item.get("description", ""),
            trait_type=item.get("trait_type", trait_type),
            background=item.get("background", ""),
            pain_points=item.get("pain_points", []),
            communication_style=item.get("communication_style", ""),
            sample_utterances=item.get("sample_utterances", []),
            reject_conditions=item.get("reject_conditions", []),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _log(self, msg: str) -> None:
        logger.info(msg)
        self.on_progress(msg)
