import io
import logging

from src.ingestion.base import DataIngestion
from src.ingestion.markdown_loader import MarkdownLoader
from src.models.schemas import RawInput

logger = logging.getLogger(__name__)


def _extract_pdf_text(data: bytes) -> str:
    """Trích text từ PDF bằng pypdf. Trả text đã nối các trang (rỗng nếu PDF scan/ảnh)."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []
    for i, page in enumerate(reader.pages):
        try:
            parts.append(page.extract_text() or "")
        except Exception as e:  # 1 trang lỗi không được làm hỏng cả file
            logger.warning("PDF page %d extract failed: %s", i, e)
    return "\n".join(parts).strip()


class PRDLoader(DataIngestion):
    """Đọc PRD (md/txt/pdf) → content để mine ra intent (PRD-as-source) → state.raw_prd_content.

    PRD chỉ đóng vai trò "source" (bóc thành prd_intents để đối chiếu với data);
    KHÔNG còn làm guidance định hướng mine data (data được mine độc lập để gap
    analysis lộ đúng Data-only / PRD-only).
    """

    def __init__(self, uploaded_file: io.BytesIO, filename: str = ""):
        self.uploaded_file = uploaded_file
        self.filename = filename

    def load(self) -> RawInput:
        # PDF: trích text thật (không thể decode như văn bản thường).
        if self.filename.lower().endswith(".pdf"):
            content = _extract_pdf_text(self.uploaded_file.read())
            if not content:
                raise ValueError(
                    "Không trích được text từ PDF (có thể là PDF scan/ảnh). "
                    "Hãy dùng PDF có text, hoặc chuyển sang .md/.txt."
                )
            return RawInput(
                source_type="prd",
                content=content,
                metadata={"filename": self.filename},
            )

        # md/txt: tái dùng MarkdownLoader để trích text PRD.
        raw_input = MarkdownLoader(self.uploaded_file, self.filename).load()
        return RawInput(
            source_type="prd",
            content=raw_input.content,
            metadata={"filename": self.filename},
        )
