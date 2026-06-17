import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.deps import get_memory, get_state
from src.llm.factory import create_llm_client
from src.models.schemas import Persona
from src.pipeline.persona_generator import PersonaAgent

router = APIRouter(prefix="/api/personas", tags=["personas"])

AGENT_NAME = "persona"


class GenerateRequest(BaseModel):
    model: str = "gemini"
    api_key: str
    guidance: str = ""


class RegenerateSingleRequest(BaseModel):
    model: str = "gemini"
    api_key: str
    persona_id: str
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


@router.delete("/{persona_id}")
def delete_persona(persona_id: str):
    state = get_state()
    persona = next((p for p in state.personas if p.id == persona_id), None)
    if not persona:
        raise HTTPException(404, f"Không tìm thấy persona: {persona_id}")
    persona.status = "deleted"
    return {"status": "deleted", "id": persona_id}


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

    agent = PersonaAgent(llm, memory=get_memory(AGENT_NAME))
    loop = asyncio.new_event_loop()
    try:
        results = loop.run_until_complete(agent.run(approved, req.guidance))
    except Exception as e:
        raise HTTPException(500, f"Lỗi sinh Persona: {e}")
    finally:
        loop.close()
    state.personas = [Persona(**r) for r in results]
    return results


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

    agent = PersonaAgent(llm, memory=get_memory(AGENT_NAME))
    loop = asyncio.new_event_loop()
    try:
        results = loop.run_until_complete(agent.run(approved, req.guidance))
    except Exception as e:
        raise HTTPException(500, f"Lỗi regenerate: {e}")
    finally:
        loop.close()
    state.personas = [Persona(**r) for r in results]
    return results


@router.post("/regenerate-single")
def regenerate_single_persona(req: RegenerateSingleRequest):
    state = get_state()
    target = next((p for p in state.personas if p.id == req.persona_id and p.status != "deleted"), None)
    if not target:
        raise HTTPException(404, f"Không tìm thấy persona: {req.persona_id}")

    intent = next((i for i in state.intents if i.id == target.intent_id and i.status != "deleted"), None)
    if not intent:
        raise HTTPException(400, "Intent của persona này không còn tồn tại")

    try:
        llm = create_llm_client(req.model, req.api_key)
    except ValueError as e:
        raise HTTPException(400, str(e))

    agent = PersonaAgent(llm, memory=get_memory(AGENT_NAME))
    if req.guidance:
        agent.add_feedback(f"Regenerate persona '{target.name}': {req.guidance}")

    loop = asyncio.new_event_loop()
    try:
        results = loop.run_until_complete(agent.run_single(intent, req.guidance))
    except Exception as e:
        raise HTTPException(500, f"Lỗi regenerate: {e}")
    finally:
        loop.close()

    if not results:
        raise HTTPException(500, "LLM không sinh được persona mới")

    target.status = "deleted"
    new_persona = Persona(**results[0])
    state.personas.append(new_persona)
    return new_persona.model_dump()
