import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.deps import get_state
from src.llm.factory import create_llm_client
from src.pipeline.intent_extractor import IntentExtractor
from src.config import settings

router = APIRouter(prefix="/api/intents", tags=["intents"])


class LLMConfig(BaseModel):
    model: str = "gemini"
    api_key: str


class RegenerateRequest(BaseModel):
    model: str = "gemini"
    api_key: str
    guidance: str = ""


class IntentUpdate(BaseModel):
    id: str
    context: str | None = None
    goal: str | None = None
    status: str | None = None


class BatchUpdate(BaseModel):
    updates: list[IntentUpdate]


@router.get("")
def list_intents():
    state = get_state()
    return [i.model_dump() for i in state.intents if i.status != "deleted"]


@router.post("/extract")
def extract_intents(config: LLMConfig):
    state = get_state()
    if not state.raw_input:
        raise HTTPException(400, "Chưa có dữ liệu đầu vào")
    try:
        llm = create_llm_client(config.model, config.api_key)
    except ValueError as e:
        raise HTTPException(400, str(e))

    extractor = IntentExtractor(llm, max_chunk_tokens=settings.chunk_max_tokens)
    loop = asyncio.new_event_loop()
    try:
        intents = loop.run_until_complete(extractor.extract(state.raw_input))
        state.intents = intents
    except Exception as e:
        raise HTTPException(500, f"Lỗi sinh Intent: {e}")
    finally:
        loop.close()
    return [i.model_dump() for i in state.intents]


@router.put("")
def update_intents(body: BatchUpdate):
    state = get_state()
    intent_map = {i.id: i for i in state.intents}
    for upd in body.updates:
        intent = intent_map.get(upd.id)
        if not intent:
            continue
        if upd.context is not None:
            intent.context = upd.context
        if upd.goal is not None:
            intent.goal = upd.goal
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
    state = get_state()
    if not state.raw_input:
        raise HTTPException(400, "Chưa có dữ liệu đầu vào")
    try:
        llm = create_llm_client(req.model, req.api_key)
    except ValueError as e:
        raise HTTPException(400, str(e))

    extractor = IntentExtractor(llm, max_chunk_tokens=settings.chunk_max_tokens)
    loop = asyncio.new_event_loop()
    try:
        state.intents = loop.run_until_complete(
            extractor.regenerate(state.intents, state.raw_input, req.guidance)
        )
    except Exception as e:
        raise HTTPException(500, f"Lỗi regenerate: {e}")
    finally:
        loop.close()
    return [i.model_dump() for i in state.intents]
