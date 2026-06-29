import io

from src.ingestion.base import DataIngestion
from src.models.schemas import RawInput


class MarkdownLoader(DataIngestion):
    """Đọc md/txt: giữ NGUYÊN VĂN (không strip cú pháp markdown).

    Cú pháp markdown (#, *, code fence, link...) được giữ lại để LLM tự hiểu cấu
    trúc tài liệu khi bóc intent — tránh mất nội dung (vd khối code/bảng).
    """

    def __init__(self, uploaded_file: io.BytesIO, filename: str = ""):
        self.uploaded_file = uploaded_file
        self.filename = filename

    def load(self) -> RawInput:
        raw = self.uploaded_file.read()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        content = raw.strip()
        if not content:
            raise ValueError("File không có nội dung text")
        return RawInput(
            source_type="text",
            content=content,
            metadata={"filename": self.filename},
        )
