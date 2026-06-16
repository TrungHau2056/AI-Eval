import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.deps import get_state
from src.llm.factory import create_llm_client
from src.pipeline.test_prompt_generator import TestCasePromptGenerator

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


class GenerateRequest(BaseModel):
    model: str = "gemini"
    api_key: str
    guidance: str = ""


class PromptUpdate(BaseModel):
    id: str
    prompt_text: str | None = None
    status: str | None = None


class BatchUpdate(BaseModel):
    updates: list[PromptUpdate]


@router.get("")
def list_prompts():
    state = get_state()
    return [t.model_dump() for t in state.test_prompts if t.status != "deleted"]


@router.post("/generate")
def generate_prompts(req: GenerateRequest):
    state = get_state()
    approved_intents = [i for i in state.intents if i.status != "deleted"]
    approved_personas = [p for p in state.personas if p.status != "deleted"]
    if not approved_intents or not approved_personas:
        raise HTTPException(400, "Chưa có Intent/Persona nào được duyệt")
    try:
        llm = create_llm_client(req.model, req.api_key)
    except ValueError as e:
        raise HTTPException(400, str(e))

    gen = TestCasePromptGenerator(llm)
    loop = asyncio.new_event_loop()
    try:
        state.test_prompts = loop.run_until_complete(
            gen.generate(approved_intents, approved_personas, req.guidance)
        )
    except Exception as e:
        raise HTTPException(500, f"Lỗi sinh Test Prompt: {e}")
    finally:
        loop.close()
    return [t.model_dump() for t in state.test_prompts]


@router.put("")
def update_prompts(body: BatchUpdate):
    state = get_state()
    prompt_map = {t.id: t for t in state.test_prompts}
    for upd in body.updates:
        prompt = prompt_map.get(upd.id)
        if not prompt:
            continue
        if upd.prompt_text is not None:
            prompt.prompt_text = upd.prompt_text
        if upd.status is not None:
            prompt.status = upd.status
        if prompt.status == "generated":
            prompt.status = "edited"
    return {"status": "ok"}


@router.post("/regenerate")
def regenerate_prompts(req: GenerateRequest):
    state = get_state()
    approved_intents = [i for i in state.intents if i.status != "deleted"]
    approved_personas = [p for p in state.personas if p.status != "deleted"]
    if not approved_intents or not approved_personas:
        raise HTTPException(400, "Chưa có Intent/Persona nào được duyệt")
    try:
        llm = create_llm_client(req.model, req.api_key)
    except ValueError as e:
        raise HTTPException(400, str(e))

    gen = TestCasePromptGenerator(llm)
    loop = asyncio.new_event_loop()
    try:
        state.test_prompts = loop.run_until_complete(
            gen.generate(approved_intents, approved_personas, req.guidance)
        )
    except Exception as e:
        raise HTTPException(500, f"Lỗi regenerate: {e}")
    finally:
        loop.close()
    return [t.model_dump() for t in state.test_prompts]
