from src.ingestion.base import DataIngestion
from src.models.schemas import RawInput


class TextLoader(DataIngestion):
    def __init__(self, text: str):
        self.text = text

    def load(self) -> RawInput:
        if not self.text.strip():
            raise ValueError("Text input không được để trống")
        return RawInput(source_type="text", content=self.text.strip())
