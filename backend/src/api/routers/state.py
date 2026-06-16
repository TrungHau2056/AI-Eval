from fastapi import APIRouter

from src.api.deps import get_state, reset_state

router = APIRouter(prefix="/api/state", tags=["state"])


@router.get("")
def get_pipeline_state():
    state = get_state()
    return {
        "current_step": state.current_step,
        "has_raw_input": state.raw_input is not None,
        "input_source": state.raw_input.source_type if state.raw_input else None,
        "intents_count": len([i for i in state.intents if i.status != "deleted"]),
        "personas_count": len([p for p in state.personas if p.status != "deleted"]),
        "prompts_count": len([t for t in state.test_prompts if t.status != "deleted"]),
    }


@router.post("/reset")
def reset_pipeline():
    state = reset_state()
    return {"status": "ok", "current_step": state.current_step}
