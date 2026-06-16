import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.deps import get_state
from src.llm.factory import create_llm_client
from src.pipeline.persona_generator import PersonaGenerator

router = APIRouter(prefix="/api/personas", tags=["personas"])


class GenerateRequest(BaseModel):
    model: str = "gemini"
    api_key: str
    guidance: str = ""


class PersonaUpdate(BaseModel):
    id: str
    name: str | None = None
    description: str | None = None
    trait_type: str | None = None
    status: str | None = None


class BatchUpdate(BaseModel):
    updates: list[PersonaUpdate]


@router.get("")
def list_personas():
    state = get_state()
    return [p.model_dump() for p in state.personas if p.status != "deleted"]


@router.post("/generate")
def generate_personas(req: GenerateRequest):
    state = get_state()
    approved = [i for i in state.intents if i.status != "deleted"]
    if not approved:
        raise HTTPException(400, "Chưa có Intent nào được duyệt")
    try:
        llm = create_llm_client(req.model, req.api_key)
    except ValueError as e:
        raise HTTPException(400, str(e))

    gen = PersonaGenerator(llm)
    loop = asyncio.new_event_loop()
    try:
        state.personas = loop.run_until_complete(gen.generate(approved, req.guidance))
    except Exception as e:
        raise HTTPException(500, f"Lỗi sinh Persona: {e}")
    finally:
        loop.close()
    return [p.model_dump() for p in state.personas]


@router.put("")
def update_personas(body: BatchUpdate):
    state = get_state()
    persona_map = {p.id: p for p in state.personas}
    for upd in body.updates:
        persona = persona_map.get(upd.id)
        if not persona:
            continue
        if upd.name is not None:
            persona.name = upd.name
        if upd.description is not None:
            persona.description = upd.description
        if upd.trait_type is not None:
            persona.trait_type = upd.trait_type
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
    state = get_state()
    approved = [i for i in state.intents if i.status != "deleted"]
    if not approved:
        raise HTTPException(400, "Chưa có Intent nào được duyệt")
    try:
        llm = create_llm_client(req.model, req.api_key)
    except ValueError as e:
        raise HTTPException(400, str(e))

    gen = PersonaGenerator(llm)
    loop = asyncio.new_event_loop()
    try:
        state.personas = loop.run_until_complete(gen.generate(approved, req.guidance))
    except Exception as e:
        raise HTTPException(500, f"Lỗi regenerate: {e}")
    finally:
        loop.close()
    return [p.model_dump() for p in state.personas]
