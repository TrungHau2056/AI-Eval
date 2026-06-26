import io
import re

from src.ingestion.base import DataIngestion
from src.models.schemas import RawInput

_HEADING = re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE)
_BOLD_ITALIC = re.compile(r"(\*{1,3}|_{1,3})(.+?)\1", re.DOTALL)
_INLINE_CODE = re.compile(r"`([^`]*)`")
_CODE_FENCE = re.compile(r"```.*?```", re.DOTALL)
_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_BLOCKQUOTE = re.compile(r"^\s{0,3}>\s?", re.MULTILINE)
_LIST_MARKER = re.compile(r"^\s{0,3}([-*+]|\d+\.)\s+", re.MULTILINE)


def strip_markdown(text: str) -> str:
    """Bỏ cú pháp markdown nhẹ, giữ lại nội dung text."""
    text = _CODE_FENCE.sub("", text)
    text = _IMAGE.sub(r"\1", text)
    text = _LINK.sub(r"\1", text)
    text = _HEADING.sub("", text)
    text = _BLOCKQUOTE.sub("", text)
    text = _LIST_MARKER.sub("", text)
    text = _BOLD_ITALIC.sub(r"\2", text)
    text = _INLINE_CODE.sub(r"\1", text)
    return text.strip()


class MarkdownLoader(DataIngestion):
    """Đọc md/txt: md strip cú pháp nhẹ; txt giữ nguyên text."""

    def __init__(self, uploaded_file: io.BytesIO, filename: str = ""):
        self.uploaded_file = uploaded_file
        self.filename = filename

    def load(self) -> RawInput:
        raw = self.uploaded_file.read()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        is_md = self.filename.lower().endswith((".md", ".markdown"))
        content = strip_markdown(raw) if is_md else raw.strip()
        if not content:
            raise ValueError("File không có nội dung text")
        return RawInput(
            source_type="text",
            content=content,
            metadata={"filename": self.filename},
        )
