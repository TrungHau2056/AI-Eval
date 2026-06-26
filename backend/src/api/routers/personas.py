import asyncio
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.deps import get_memory, get_state
from src.config import settings
from src.llm.factory import create_llm_client
from src.models.schemas import Persona
from src.pipeline.persona_generator import PersonaAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/personas", tags=["personas"])

AGENT_NAME = "persona"


class GenerateRequest(BaseModel):
    model: str = "openai"
    api_key: str = ""
    guidance: str = ""


class RegenerateSingleRequest(BaseModel):
    model: str = "openai"
    api_key: str = ""
    persona_id: str
    guidance: str = ""


class PersonaUpdate(BaseModel):
    id: str
    persona_type: str | None = None
    trigger: str | None = None
    utterance: str | None = None
    frequency: str | None = None
    pain: str | None = None
    reject: str | None = None
    expected_behavior: str | None = None
    status: str | None = None


class BatchUpdate(BaseModel):
    updates: list[PersonaUpdate]


@router.get("")
def list_personas():
    state = get_state()
    return [p.model_dump() for p in state.personas if p.status != "deleted"]


@router.delete("/{persona_id}")
def delete_persona(persona_id: str):
    state = get_state()
    persona = next((p for p in state.personas if p.id == persona_id), None)
    if not persona:
        raise HTTPException(404, f"Không tìm thấy persona: {persona_id}")
    persona.status = "deleted"
    return {"status": "deleted", "id": persona_id}


def _resolve_api_key(model: str, api_key: str) -> str:
    if api_key:
        return api_key
    if model == "openai":
        key = settings.openai_api_key
    else:
        key = settings.gemini_api_key
    if not key:
        raise HTTPException(400, f"Chua co API key cho {model}. Nhap API key o sidebar hoac cau hinh trong .env")
    return key


@router.post("/generate")
def generate_personas(req: GenerateRequest):
    logger.info("POST /api/personas/generate | model=%s", req.model)
    state = get_state()
    approved = [i for i in state.intents if i.status != "deleted"]
    if not approved:
        raise HTTPException(400, "Chưa có Intent nào được duyệt")
    logger.info("Found %d approved intents for persona generation", len(approved))
    api_key = _resolve_api_key(req.model, req.api_key)
    try:
        llm = create_llm_client(req.model, api_key)
    except ValueError as e:
        raise HTTPException(400, str(e))

    agent = PersonaAgent(llm, memory=get_memory(AGENT_NAME))
    loop = asyncio.new_event_loop()
    try:
        logger.info("Starting PersonaAgent.run() ...")
        results = loop.run_until_complete(agent.run(approved, req.guidance))
        logger.info("PersonaAgent.run() completed | results=%d personas", len(results))
    except Exception as e:
        logger.error("PersonaAgent.run() failed: %s", e, exc_info=True)
        raise HTTPException(500, f"Lỗi sinh Persona: {e}")
    finally:
        loop.close()
    state.personas = [Persona(**r) for r in results]
    logger.info("Stored %d personas in state", len(state.personas))
    return results


@router.put("")
def update_personas(body: BatchUpdate):
    state = get_state()
    persona_map = {p.id: p for p in state.personas}
    for upd in body.updates:
        persona = persona_map.get(upd.id)
        if not persona:
            continue
        if upd.persona_type is not None:
            persona.persona_type = upd.persona_type
        if upd.trigger is not None:
            persona.trigger = upd.trigger
        if upd.utterance is not None:
            persona.utterance = upd.utterance
        if upd.frequency is not None:
            persona.frequency = upd.frequency
        if upd.pain is not None:
            persona.pain = upd.pain
        if upd.reject is not None:
            persona.reject = upd.reject
        if upd.expected_behavior is not None:
            persona.expected_behavior = upd.expected_behavior
        if upd.status is not None:
            persona.status = upd.status
        if persona.status == "generated":
            persona.status = "edited"
    return {"status": "ok"}


@router.post("/approve")
def approve_personas():
    state = get_state()
    for p in state.personas:
        if p.status in ("generated", "edited"):
            p.status = "approved"
    state.current_step = 3
    return {"status": "ok", "approved": len([p for p in state.personas if p.status == "approved"])}


@router.post("/regenerate")
def regenerate_personas(req: GenerateRequest):
    logger.info("POST /api/personas/regenerate | model=%s", req.model)
    state = get_state()
    approved = [i for i in state.intents if i.status != "deleted"]
    if not approved:
        raise HTTPException(400, "Chưa có Intent nào được duyệt")
    api_key = _resolve_api_key(req.model, req.api_key)
    try:
        llm = create_llm_client(req.model, api_key)
    except ValueError as e:
        raise HTTPException(400, str(e))

    agent = PersonaAgent(llm, memory=get_memory(AGENT_NAME))
    loop = asyncio.new_event_loop()
    try:
        logger.info("Starting PersonaAgent.run() for regenerate ...")
        results = loop.run_until_complete(agent.run(approved, req.guidance))
        logger.info("Regenerate completed | results=%d personas", len(results))
    except Exception as e:
        logger.error("Regenerate personas failed: %s", e, exc_info=True)
        raise HTTPException(500, f"Lỗi regenerate: {e}")
    finally:
        loop.close()
    state.personas = [Persona(**r) for r in results]
    return results


@router.post("/regenerate-single")
def regenerate_single_persona(req: RegenerateSingleRequest):
    logger.info("POST /api/personas/regenerate-single | persona_id=%s", req.persona_id)
    state = get_state()
    target = next((p for p in state.personas if p.id == req.persona_id and p.status != "deleted"), None)
    if not target:
        raise HTTPException(404, f"Không tìm thấy persona: {req.persona_id}")

    intent = next((i for i in state.intents if i.id == target.intent_id and i.status != "deleted"), None)
    if not intent:
        raise HTTPException(400, "Intent của persona này không còn tồn tại")

    api_key = _resolve_api_key(req.model, req.api_key)
    try:
        llm = create_llm_client(req.model, api_key)
    except ValueError as e:
        raise HTTPException(400, str(e))

    agent = PersonaAgent(llm, memory=get_memory(AGENT_NAME))
    if req.guidance:
        agent.add_feedback(f"Regenerate persona '{target.trigger}': {req.guidance}")

    loop = asyncio.new_event_loop()
    try:
        logger.info("Starting PersonaAgent.run_single() for persona_id=%s ...", req.persona_id)
        results = loop.run_until_complete(agent.run_single(intent, req.guidance))
        logger.info("Regenerate-single completed | results=%d", len(results))
    except Exception as e:
        logger.error("Regenerate-single persona failed: %s", e, exc_info=True)
        raise HTTPException(500, f"Lỗi regenerate: {e}")
    finally:
        loop.close()

    if not results:
        raise HTTPException(500, "LLM không sinh được persona mới")

    target.status = "deleted"
    new_persona = Persona(**results[0])
    state.personas.append(new_persona)
    logger.info("Replaced persona %s with new persona %s", req.persona_id, new_persona.id)
    return new_persona.model_dump()
