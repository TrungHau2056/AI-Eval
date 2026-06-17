import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.deps import get_memory, get_state
from src.llm.factory import create_llm_client
from src.models.schemas import TestCasePrompt
from src.pipeline.test_prompt_generator import TestCaseAgent

router = APIRouter(prefix="/api/prompts", tags=["prompts"])

AGENT_NAME = "test_case"


class GenerateRequest(BaseModel):
    model: str = "gemini"
    api_key: str
    guidance: str = ""


class RegenerateSingleRequest(BaseModel):
    model: str = "gemini"
    api_key: str
    test_case_id: str
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


@router.delete("/{test_case_id}")
def delete_prompt(test_case_id: str):
    state = get_state()
    prompt = next((t for t in state.test_prompts if t.id == test_case_id), None)
    if not prompt:
        raise HTTPException(404, f"Không tìm thấy test case: {test_case_id}")
    prompt.status = "deleted"
    return {"status": "deleted", "id": test_case_id}


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

    agent = TestCaseAgent(llm, memory=get_memory(AGENT_NAME))
    loop = asyncio.new_event_loop()
    try:
        results = loop.run_until_complete(
            agent.run(approved_personas, approved_intents, req.guidance)
        )
    except Exception as e:
        raise HTTPException(500, f"Lỗi sinh Test Case: {e}")
    finally:
        loop.close()
    state.test_prompts = [TestCasePrompt(**r) for r in results]
    return results


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

    agent = TestCaseAgent(llm, memory=get_memory(AGENT_NAME))
    loop = asyncio.new_event_loop()
    try:
        results = loop.run_until_complete(
            agent.run(approved_personas, approved_intents, req.guidance)
        )
    except Exception as e:
        raise HTTPException(500, f"Lỗi regenerate: {e}")
    finally:
        loop.close()
    state.test_prompts = [TestCasePrompt(**r) for r in results]
    return results


@router.post("/regenerate-single")
def regenerate_single_prompt(req: RegenerateSingleRequest):
    state = get_state()
    target = next((t for t in state.test_prompts if t.id == req.test_case_id and t.status != "deleted"), None)
    if not target:
        raise HTTPException(404, f"Không tìm thấy test case: {req.test_case_id}")

    intent = next((i for i in state.intents if i.id == target.intent_id and i.status != "deleted"), None)
    persona = next((p for p in state.personas if p.id == target.persona_id and p.status != "deleted"), None)
    if not intent or not persona:
        raise HTTPException(400, "Intent hoặc Persona của test case này không còn tồn tại")

    try:
        llm = create_llm_client(req.model, req.api_key)
    except ValueError as e:
        raise HTTPException(400, str(e))

    agent = TestCaseAgent(llm, memory=get_memory(AGENT_NAME))
    if req.guidance:
        agent.add_feedback(f"Regenerate test case '{target.prompt_text}': {req.guidance}")

    loop = asyncio.new_event_loop()
    try:
        results = loop.run_until_complete(
            agent.run_single(persona, intent, req.guidance)
        )
    except Exception as e:
        raise HTTPException(500, f"Lỗi regenerate: {e}")
    finally:
        loop.close()

    if not results:
        raise HTTPException(500, "LLM không sinh được test case mới")

    target.status = "deleted"
    new_tc = TestCasePrompt(**results[0])
    state.test_prompts.append(new_tc)
    return new_tc.model_dump()
