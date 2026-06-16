from __future__ import annotations

import uuid
from pydantic import BaseModel, Field


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


class Intent(BaseModel):
    id: str = Field(default_factory=_new_id)
    context: str
    goal: str
    evidence: list[str] = Field(default_factory=list)
    status: str = "generated"


class Persona(BaseModel):
    id: str = Field(default_factory=_new_id)
    intent_id: str
    name: str
    description: str
    trait_type: str  # "easy" | "hard"
    status: str = "generated"


class TestCasePrompt(BaseModel):
    id: str = Field(default_factory=_new_id)
    persona_id: str
    intent_id: str
    prompt_text: str
    status: str = "generated"


class RawInput(BaseModel):
    id: str = Field(default_factory=_new_id)
    source_type: str  # "csv" | "text" | "crawl"
    content: str
    metadata: dict = Field(default_factory=dict)


class PipelineState(BaseModel):
    raw_input: RawInput | None = None
    intents: list[Intent] = Field(default_factory=list)
    personas: list[Persona] = Field(default_factory=list)
    test_prompts: list[TestCasePrompt] = Field(default_factory=list)
    current_step: int = 0  # 0=input, 1=intent, 2=persona, 3=prompt
