"""
Persona Agent Schemas
=====================
Schemas riêng cho persona agent loop.
Tách biệt khỏi src/models/schemas.py để tránh conflict với team khác.

Nếu trong tương lai cần integrate với PipelineState chính,
chỉ cần import Intent/Persona từ src.models.schemas và cast/convert.
"""
from __future__ import annotations

import uuid
from typing import Any
from pydantic import BaseModel, Field

from src.config import settings


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


# ---------------------------------------------------------------------------
# Input types (mirror cấu trúc của team intent, nhưng chỉ dùng những field cần)
# ---------------------------------------------------------------------------

class IntentInput(BaseModel):
    """
    Đầu vào từ bước Intent Extraction.
    Tương thích với Intent schema của team chính (context, goal, evidence).
    Dùng cho cả:
      - load từ file JSON/CSV do team intent export ra
      - nhận trực tiếp từ pipeline state qua API
    """
    id: str = Field(default_factory=_new_id)
    context: str = Field(..., description="Bối cảnh / tình huống người dùng")
    goal: str = Field(..., description="Mục tiêu người dùng muốn đạt được")
    evidence: list[str] = Field(default_factory=list, description="Trích dẫn gốc hỗ trợ intent")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IntentInput":
        """Load từ dict — tương thích với output của IntentExtractor."""
        return cls(
            id=data.get("id", _new_id()),
            context=data["context"],
            goal=data["goal"],
            evidence=data.get("evidence", []),
        )


class RubricCriterion(BaseModel):
    """Một tiêu chí trong rubric chấm điểm persona."""
    id: str = Field(default_factory=_new_id)
    name: str = Field(..., description="Tên tiêu chí (VD: 'Tính chân thực')")
    description: str = Field(..., description="Mô tả tiêu chí")
    weight: float = Field(default=1.0, ge=0.0, description="Trọng số điểm")
    max_score: int = Field(default=3, ge=1, le=5, description="Điểm tối đa")


class RubricInput(BaseModel):
    """
    Rubric chấm điểm persona — do researcher định nghĩa.
    Agent sẽ dùng rubric này để đánh giá và cải thiện persona trong loop.
    """
    name: str = Field(default="Persona Evaluation Rubric")
    version: str = Field(default="v0.1")
    criteria: list[RubricCriterion] = Field(default_factory=list)
    pass_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Ngưỡng điểm tổng để persona đạt (0.0-1.0)",
    )


# ---------------------------------------------------------------------------
# Agent internal types
# ---------------------------------------------------------------------------

class PersonaDraft(BaseModel):
    """Một bản draft persona do LLM sinh ra trong agent loop."""
    id: str = Field(default_factory=_new_id)
    intent_id: str
    name: str
    description: str
    trait_type: str = Field(..., description="'easy' hoặc 'hard'")
    background: str = Field(default="", description="Tiểu sử ngắn")
    pain_points: list[str] = Field(default_factory=list, description="Vấn đề, nỗi đau của persona")
    communication_style: str = Field(default="", description="Phong cách giao tiếp")
    sample_utterances: list[str] = Field(
        default_factory=list,
        description="Ví dụ câu hỏi/phát ngôn chân thực của persona",
    )
    reject_conditions: list[str] = Field(
        default_factory=list,
        description="Điều kiện từ chối — khi nào persona KHÔNG nên dùng",
    )


class CriterionScore(BaseModel):
    """Điểm cho một tiêu chí trong rubric."""
    criterion_id: str
    criterion_name: str
    score: int = Field(..., ge=0)
    max_score: int = Field(..., ge=1)
    reasoning: str = Field(default="")
    improvement_suggestions: list[str] = Field(default_factory=list)


class PersonaEvaluation(BaseModel):
    """Kết quả đánh giá một persona theo rubric."""
    persona_id: str
    criterion_scores: list[CriterionScore] = Field(default_factory=list)
    total_score: float = Field(default=0.0)
    max_possible: float = Field(default=0.0)
    normalized_score: float = Field(default=0.0, description="0.0-1.0")
    passed: bool = False
    overall_feedback: str = Field(default="")
    iteration: int = Field(default=1)

    def compute_totals(self) -> None:
        """Tính lại total/normalized sau khi cập nhật criterion_scores."""
        self.total_score = sum(
            cs.score * w
            for cs, w in zip(
                self.criterion_scores,
                [1.0] * len(self.criterion_scores),  # equal weight fallback
            )
        )
        self.max_possible = sum(cs.max_score for cs in self.criterion_scores)
        self.normalized_score = (
            self.total_score / self.max_possible if self.max_possible > 0 else 0.0
        )


class AgentLoopState(BaseModel):
    """Trạng thái của một agent loop cho 1 intent."""
    intent: IntentInput
    rubric: RubricInput
    current_drafts: list[PersonaDraft] = Field(default_factory=list)
    evaluations: list[PersonaEvaluation] = Field(default_factory=list)
    iteration: int = Field(default=0)
    max_iterations: int = Field(default=settings.persona_max_iterations)
    passed: bool = False
    history: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Log toàn bộ lịch sử iteration để debug",
    )


class PersonaAgentResult(BaseModel):
    """Kết quả cuối cùng của toàn bộ agent run cho nhiều intents."""
    intent_results: list[AgentLoopResult] = Field(default_factory=list)
    total_intents: int = 0
    passed_intents: int = 0
    failed_intents: int = 0
    run_metadata: dict[str, Any] = Field(default_factory=dict)


class AgentLoopResult(BaseModel):
    """Kết quả cho 1 intent sau khi agent loop kết thúc."""
    intent_id: str
    intent_goal: str
    final_personas: list[PersonaDraft] = Field(default_factory=list)
    final_evaluations: list[PersonaEvaluation] = Field(default_factory=list)
    total_iterations: int = 0
    passed: bool = False
    failure_reason: str = ""


# Fix forward reference
PersonaAgentResult.model_rebuild()
