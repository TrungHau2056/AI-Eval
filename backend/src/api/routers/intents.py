import asyncio
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.deps import get_memory, get_state
from src.config import settings
from src.llm.factory import create_llm_client
from src.models.schemas import Intent
from src.pipeline.intent_extractor import IntentAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/intents", tags=["intents"])

AGENT_NAME = "intent"


class LLMConfig(BaseModel):
    model: str = "openai"
    api_key: str = ""
    guidance: str = ""


class RegenerateRequest(BaseModel):
    model: str = "openai"
    api_key: str = ""
    guidance: str = ""


class RegenerateSingleRequest(BaseModel):
    model: str = "openai"
    api_key: str = ""
    intent_id: str
    guidance: str = ""


class IntentUpdate(BaseModel):
    id: str
    intent_name: str | None = None
    utterance: str | None = None
    moment: str | None = None
    phase: str | None = None
    status: str | None = None


class BatchUpdate(BaseModel):
    updates: list[IntentUpdate]


@router.get("")
def list_intents():
    state = get_state()
    return [i.model_dump() for i in state.intents if i.status != "deleted"]


@router.delete("/{intent_id}")
def delete_intent(intent_id: str):
    state = get_state()
    intent = next((i for i in state.intents if i.id == intent_id), None)
    if not intent:
        raise HTTPException(404, f"Khong tim thay intent: {intent_id}")
    intent.status = "deleted"
    return {"status": "deleted", "id": intent_id}


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


@router.post("/extract")
def extract_intents(config: LLMConfig):
    logger.info("POST /api/intents/extract | model=%s | guidance=%s", config.model, bool(config.guidance))
    state = get_state()
    if not state.raw_input:
        logger.warning("No raw_input in state, rejecting extract request")
        raise HTTPException(400, "Chua co du lieu dau vao")
    logger.info("raw_input present: source=%s length=%d", state.raw_input.source_type, len(state.raw_input.content))
    api_key = _resolve_api_key(config.model, config.api_key)
    logger.info("API key resolved for model=%s", config.model)
    try:
        llm = create_llm_client(config.model, api_key)
    except ValueError as e:
        logger.error("Failed to create LLM client: %s", e)
        raise HTTPException(400, str(e))

    agent = IntentAgent(llm, memory=get_memory(AGENT_NAME), max_chunk_tokens=settings.chunk_max_tokens)
    if config.guidance:
        agent.add_feedback(f"Extract intents: {config.guidance}")
        logger.info("Guidance added to agent memory")
    loop = asyncio.new_event_loop()
    try:
        logger.info("Starting IntentAgent.run() ...")
        results = loop.run_until_complete(agent.run(state.raw_input, config.guidance))
        logger.info("IntentAgent.run() completed | results=%d intents", len(results))
    except Exception as e:
        logger.error("IntentAgent.run() failed: %s", e, exc_info=True)
        raise HTTPException(500, f"Loi sinh Intent: {e}")
    finally:
        loop.close()
    state.intents = [Intent(**r) for r in results]
    logger.info("Stored %d intents in state", len(state.intents))
    return results


@router.put("")
def update_intents(body: BatchUpdate):
    state = get_state()
    intent_map = {i.id: i for i in state.intents}
    for upd in body.updates:
        intent = intent_map.get(upd.id)
        if not intent:
            continue
        if upd.intent_name is not None:
            intent.intent_name = upd.intent_name
        if upd.utterance is not None:
            intent.utterance = upd.utterance
        if upd.moment is not None:
            intent.moment = upd.moment
        if upd.phase is not None:
            intent.phase = upd.phase
        if upd.status is not None:
            intent.status = upd.status
        if intent.status == "generated":
            intent.status = "edited"
    return {"status": "ok"}


@router.post("/approve")
def approve_intents():
    state = get_state()
    for i in state.intents:
        if i.status in ("generated", "edited"):
            i.status = "approved"
    state.current_step = 2
    return {"status": "ok", "approved": len([i for i in state.intents if i.status == "approved"])}


@router.post("/regenerate")
def regenerate_intents(req: RegenerateRequest):
    logger.info("POST /api/intents/regenerate | model=%s", req.model)
    state = get_state()
    if not state.raw_input:
        raise HTTPException(400, "Chua co du lieu dau vao")
    api_key = _resolve_api_key(req.model, req.api_key)
    try:
        llm = create_llm_client(req.model, api_key)
    except ValueError as e:
        raise HTTPException(400, str(e))

    agent = IntentAgent(llm, memory=get_memory(AGENT_NAME), max_chunk_tokens=settings.chunk_max_tokens)
    if req.guidance:
        agent.add_feedback(f"Regenerate intents: {req.guidance}")

    loop = asyncio.new_event_loop()
    try:
        logger.info("Starting IntentAgent.run() for regenerate ...")
        results = loop.run_until_complete(agent.run(state.raw_input, req.guidance))
        logger.info("Regenerate completed | results=%d intents", len(results))
    except Exception as e:
        logger.error("Regenerate failed: %s", e, exc_info=True)
        raise HTTPException(500, f"Loi regenerate: {e}")
    finally:
        loop.close()
    state.intents = [Intent(**r) for r in results]
    return results


@router.post("/regenerate-single")
def regenerate_single_intent(req: RegenerateSingleRequest):
    logger.info("POST /api/intents/regenerate-single | intent_id=%s", req.intent_id)
    state = get_state()
    target = next((i for i in state.intents if i.id == req.intent_id and i.status != "deleted"), None)
    if not target:
        raise HTTPException(404, f"Khong tim thay intent: {req.intent_id}")

    if not state.raw_input:
        raise HTTPException(400, "Chua co du lieu dau vao")

    api_key = _resolve_api_key(req.model, req.api_key)
    try:
        llm = create_llm_client(req.model, api_key)
    except ValueError as e:
        raise HTTPException(400, str(e))

    agent = IntentAgent(llm, memory=get_memory(AGENT_NAME))
    if req.guidance:
        agent.add_feedback(f"Regenerate intent '{target.context} -> {target.goal}': {req.guidance}")

    loop = asyncio.new_event_loop()
    try:
        logger.info("Starting IntentAgent.run_single() for intent_id=%s ...", req.intent_id)
        results = loop.run_until_complete(agent.run_single(state.raw_input, req.guidance))
        logger.info("Regenerate-single completed | results=%d", len(results))
    except Exception as e:
        logger.error("Regenerate-single failed: %s", e, exc_info=True)
        raise HTTPException(500, f"Loi regenerate: {e}")
    finally:
        loop.close()

    if not results:
        raise HTTPException(500, "LLM khong sinh duoc intent moi")

    target.status = "deleted"
    new_intent = Intent(**results[0])
    state.intents.append(new_intent)
    logger.info("Replaced intent %s with new intent %s", req.intent_id, new_intent.id)
    return new_intent.model_dump()
