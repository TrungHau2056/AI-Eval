import io
import re

from src.ingestion.base import DataIngestion
from src.models.schemas import RawInput

_SPACE = re.compile(r"[ \t]+")


def _clean_pdf_text(text: str) -> str:
    lines = []
    for line in text.replace("\x00", "").splitlines():
        clean = _SPACE.sub(" ", line).strip()
        if clean:
            lines.append(clean)
    return "\n".join(lines).strip()


class PdfLoader(DataIngestion):
    """Extract text from a PDF using PyMuPDF."""

    def __init__(self, uploaded_file: io.BytesIO, filename: str = ""):
        self.uploaded_file = uploaded_file
        self.filename = filename

    def load(self) -> RawInput:
        try:
            import fitz  # PyMuPDF
        except ImportError as exc:
            raise RuntimeError("PyMuPDF is required to ingest PDF files. Install with `pip install PyMuPDF`.") from exc

        raw = self.uploaded_file.read()
        if not raw:
            raise ValueError("PDF file is empty")

        try:
            doc = fitz.open(stream=raw, filetype="pdf")
        except Exception as exc:
            raise ValueError(f"Cannot open PDF file: {exc}") from exc

        try:
            if doc.is_encrypted:
                raise ValueError("PDF is encrypted or password protected")

            page_texts: list[str] = []
            for page in doc:
                text = _clean_pdf_text(page.get_text("text"))
                if text:
                    page_texts.append(text)

            content = "\n---\n".join(page_texts).strip()
            page_count = doc.page_count
        finally:
            doc.close()

        if not content:
            raise ValueError("PDF does not contain extractable text")

        return RawInput(
            source_type="text",
            content=content,
            metadata={
                "filename": self.filename,
                "filetype": "pdf",
                "pages": page_count,
                "rows": len(page_texts),
            },
        )
