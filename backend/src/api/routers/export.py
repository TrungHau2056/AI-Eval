from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from src.api.deps import get_state
from src.export.exporter import Exporter

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/csv", response_class=PlainTextResponse)
def export_csv():
    state = get_state()
    return Exporter.to_csv(state.test_prompts, state.intents, state.personas)


@router.get("/markdown", response_class=PlainTextResponse)
def export_markdown():
    state = get_state()
    return Exporter.to_markdown(state.test_prompts, state.intents, state.personas)
