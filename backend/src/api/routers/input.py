import io
import logging

from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel

from src.api.deps import get_state
from src.ingestion.csv_loader import CSVLoader
from src.ingestion.text_loader import TextLoader

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/input", tags=["input"])


class TextInput(BaseModel):
    text: str


@router.post("/text")
def load_text(body: TextInput):
    logger.info("POST /api/input/text | length=%d", len(body.text))
    state = get_state()
    loader = TextLoader(body.text)
    state.raw_input = loader.load()
    state.current_step = 1
    logger.info("Text loaded | source=%s | content_length=%d", state.raw_input.source_type, len(state.raw_input.content))
    return {"status": "ok", "source_type": state.raw_input.source_type, "length": len(state.raw_input.content)}


@router.post("/csv")
def load_csv(file: UploadFile = File(...)):
    logger.info("POST /api/input/csv | filename=%s", file.filename)
    state = get_state()
    content = file.file.read()
    loader = CSVLoader(io.BytesIO(content), filename=file.filename or "upload.csv")
    state.raw_input = loader.load()
    state.current_step = 1
    logger.info("CSV loaded | source=%s | content_length=%d", state.raw_input.source_type, len(state.raw_input.content))
    return {"status": "ok", "source_type": state.raw_input.source_type, "length": len(state.raw_input.content), "metadata": state.raw_input.metadata}
