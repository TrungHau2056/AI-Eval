import logging

from fastapi import APIRouter

from src.api.deps import get_state, reset_state
from src.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/state", tags=["state"])


@router.get("")
def get_pipeline_state():
    state = get_state()
    return {
        "current_step": state.current_step,
        "has_raw_input": state.raw_input is not None,
        "input_source": state.raw_input.source_type if state.raw_input else None,
        "intents": [i.model_dump() for i in state.intents if i.status != "deleted"],
        "personas": [p.model_dump() for p in state.personas if p.status != "deleted"],
        "test_cases": [t.model_dump() for t in state.test_prompts if t.status != "deleted"],
        "api_key_configured": {
            "openai": bool(settings.openai_api_key),
            "gemini": bool(settings.gemini_api_key),
        },
    }


@router.post("/reset")
def reset_pipeline():
    logger.info("POST /api/state/reset")
    state = reset_state()
    return {"status": "ok", "current_step": state.current_step}
