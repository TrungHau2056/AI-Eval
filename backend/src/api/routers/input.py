import io

from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel

from src.api.deps import get_state
from src.ingestion.csv_loader import CSVLoader
from src.ingestion.text_loader import TextLoader

router = APIRouter(prefix="/api/input", tags=["input"])


class TextInput(BaseModel):
    text: str


@router.post("/text")
def load_text(body: TextInput):
    state = get_state()
    loader = TextLoader(body.text)
    state.raw_input = loader.load()
    state.current_step = 1
    return {"status": "ok", "source_type": state.raw_input.source_type, "length": len(state.raw_input.content)}


@router.post("/csv")
def load_csv(file: UploadFile = File(...)):
    state = get_state()
    content = file.file.read()
    loader = CSVLoader(io.BytesIO(content), filename=file.filename or "upload.csv")
    state.raw_input = loader.load()
    state.current_step = 1
    return {"status": "ok", "source_type": state.raw_input.source_type, "length": len(state.raw_input.content), "metadata": state.raw_input.metadata}
