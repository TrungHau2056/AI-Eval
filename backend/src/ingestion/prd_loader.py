import io

from src.ingestion.base import DataIngestion
from src.ingestion.markdown_loader import MarkdownLoader
from src.ingestion.pdf_loader import PdfLoader
from src.models.schemas import RawInput


class PRDLoader(DataIngestion):
    """Read PRD files (md/txt/pdf) into state.raw_prd_content."""

    def __init__(self, uploaded_file: io.BytesIO, filename: str = ""):
        self.uploaded_file = uploaded_file
        self.filename = filename

    def load(self) -> RawInput:
        if self.filename.lower().endswith(".pdf"):
            raw_input = PdfLoader(self.uploaded_file, self.filename).load()
        else:
            raw_input = MarkdownLoader(self.uploaded_file, self.filename).load()

        return RawInput(
            source_type="prd",
            content=raw_input.content,
            metadata={**raw_input.metadata, "filename": self.filename},
        )
