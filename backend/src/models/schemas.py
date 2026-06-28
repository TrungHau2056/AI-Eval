from __future__ import annotations

import uuid
from pydantic import BaseModel, Field


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


# --- Frontend-facing models (match frontend/src/types.ts) ---


class FEIntent(BaseModel):
    id: str = Field(default_factory=_new_id)
    name: str = ""
    phase: str = "SUPPORT"
    utterance: str = ""
    triggerMoment: str = ""
    selected: bool = True
    # Gap analysis (Phase 1)
    source: str = "data"  # data | prd
    coverage: str = ""  # confirmed | prd_only | data_only | "" (standalone)
    matchedIds: list[str] = Field(default_factory=list)


class FEPersona(BaseModel):
    id: str = Field(default_factory=_new_id)
    intentId: str = ""
    type: str = "happy"  # happy | edge
    name: str = ""
    trigger: str = ""
    utterance: str = ""
    frequency: int = 0
    frequencyText: str = ""
    pain: str = ""
    reject: str = ""
    expectedAIBehavior: str = ""


class FETestCase(BaseModel):
    id: str = Field(default_factory=_new_id)
    intentName: str = ""
    personaName: str = ""
    simulatedPrompt: str = ""
    expectedOutcome: str = ""
    selected: bool = True
    status: str = "pending"  # pending | running | passed | failed
    logs: list[str] = Field(default_factory=list)
    goal: str = ""


# --- Internal pipeline models (used by pipeline agents) ---


class Intent(BaseModel):
    id: str = Field(default_factory=_new_id)
    intent_num: int = 0
    intent_name: str = ""
    utterance: str = ""
    moment: str = ""
    source: str = ""
    phase: str = ""
    raw_observation: str = ""
    why_valid: str = ""
    context: str = ""
    goal: str = ""
    evidence: list[str] = Field(default_factory=list)
    status: str = "generated"


class Persona(BaseModel):
    id: str = Field(default_factory=_new_id)
    intent_id: str = ""
    intent_num: int = 0
    intent_name: str = ""
    persona_num: int = 0
    persona_type: str = ""
    trigger: str = ""
    utterance: str = ""
    frequency: str = ""
    pain: str = ""
    reject: str = ""
    special_situation: str = ""
    research_source: str = ""
    why_different: str = ""
    expected_behavior: str = ""
    ai_response_example: str = ""
    name: str = ""
    description: str = ""
    trait_type: str = ""
    status: str = "generated"


class TestCasePrompt(BaseModel):
    id: str = Field(default_factory=_new_id)
    persona_id: str = ""
    intent_id: str = ""
    test_case_id: str = ""
    intent_num: int = 0
    intent_name: str = ""
    case_num: int = 0
    title_user_moment: str = ""
    persona: str = ""
    goal: str = ""
    start: str = ""
    end_expected_outcome: str = ""
    prompt_text: str = ""
    status: str = "generated"


class RawInput(BaseModel):
    id: str = Field(default_factory=_new_id)
    source_type: str = "text"
    content: str = ""
    domain: str = ""
    metadata: dict = Field(default_factory=dict)


class PipelineState(BaseModel):
    model_config = {"populate_by_name": True}
    raw_input: RawInput | None = None
    # PRD-as-source: content để mine thành prd_intents (đối chiếu với data)
    raw_prd_content: str = ""
    # Crawled social content theo platform: {platform_slug: posts_json} — stored on
    # crawl-only, consumed by /api/discover. Mỗi platform 1 key để crawl nhiều nền
    # tảng không ghi đè nhau.
    raw_social_content: dict[str, str] = Field(default_factory=dict)
    # Frontend-facing state
    api_key: str = ""
    domain: str = "qa-env-01.local"
    ai_model: str = "gemini"
    intents: list[FEIntent] = Field(default_factory=list)
    personas: list[FEPersona] = Field(default_factory=list)
    test_cases: list[FETestCase] = Field(default_factory=list)
    # Internal pipeline state (used to pass rich data between pipeline stages)
    internal_intents: list[Intent] = Field(default_factory=list)
    internal_personas: list[Persona] = Field(default_factory=list)
    internal_test_prompts: list[TestCasePrompt] = Field(default_factory=list)
    current_step: int = 0
    trace_id: str = ""

