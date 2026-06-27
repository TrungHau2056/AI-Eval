from fastapi import APIRouter
from fastapi.responses import PlainTextResponse, Response

from src.api.deps import get_state
from src.export.exporter import Exporter

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/csv", response_class=PlainTextResponse)
def export_csv():
    state = get_state()
    return Exporter.to_csv(state.internal_test_prompts, state.internal_intents, state.internal_personas)


@router.get("/markdown", response_class=PlainTextResponse)
def export_markdown():
    state = get_state()
    return Exporter.to_markdown(state.internal_test_prompts, state.internal_intents, state.internal_personas)


@router.get("/intents/json")
def export_intents_json():
    state = get_state()
    body = Exporter.intents_to_json(state.intents, state.internal_intents)
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="extracted_intents.json"'},
    )


@router.get("/intents/csv", response_class=PlainTextResponse)
def export_intents_csv():
    state = get_state()
    csv_body = Exporter.intents_to_csv(state.intents, state.internal_intents)
    return Response(
        content=csv_body,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="extracted_intents.csv"'},
    )
