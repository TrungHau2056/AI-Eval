import io

from src.ingestion.base import DataIngestion
from src.ingestion.markdown_loader import MarkdownLoader
from src.models.schemas import RawInput


class PRDLoader(DataIngestion):
    """Đọc PRD (md/txt) → content để mine ra intent (PRD-as-source) → state.raw_prd_content.

    PRD chỉ đóng vai trò "source" (bóc thành prd_intents để đối chiếu với data);
    KHÔNG còn làm guidance định hướng mine data (data được mine độc lập để gap
    analysis lộ đúng Data-only / PRD-only).
    """

    def __init__(self, uploaded_file: io.BytesIO, filename: str = ""):
        self.uploaded_file = uploaded_file
        self.filename = filename

    def load(self) -> RawInput:
        # Tái dùng MarkdownLoader để trích text PRD.
        raw_input = MarkdownLoader(self.uploaded_file, self.filename).load()
        return RawInput(
            source_type="prd",
            content=raw_input.content,
            metadata={"filename": self.filename},
        )
