import io
import json

from src.ingestion.base import DataIngestion
from src.models.schemas import RawInput

# Whitelist key chứa text hữu ích (case-insensitive)
TEXT_KEYS = {"text", "content", "comment", "message", "body", "caption", "title"}


def _extract_utterances(node, out: list[str]) -> None:
    """Duyệt đệ quy json, gom giá trị string theo whitelist key."""
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, str):
                if key.lower() in TEXT_KEYS and value.strip():
                    out.append(value.strip())
            else:
                _extract_utterances(value, out)
    elif isinstance(node, list):
        for item in node:
            _extract_utterances(item, out)


class JsonLoader(DataIngestion):
    """Đọc json/jsonl, flatten field text theo whitelist key (nested → đệ quy)."""

    def __init__(self, uploaded_file: io.BytesIO, filename: str = ""):
        self.uploaded_file = uploaded_file
        self.filename = filename

    def _parse(self, raw: str):
        raw = raw.strip()
        if not raw:
            raise ValueError("JSON rỗng")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Thử jsonl: mỗi dòng 1 object
            records = []
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                records.append(json.loads(line))
            if not records:
                raise
            return records

    def load(self) -> RawInput:
        raw = self.uploaded_file.read()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        data = self._parse(raw)
        utterances: list[str] = []
        _extract_utterances(data, utterances)
        if not utterances:
            raise ValueError("JSON không chứa field text hợp lệ")
        content = "\n---\n".join(utterances)
        return RawInput(
            source_type="survey",
            content=content,
            metadata={"filename": self.filename, "rows": len(utterances)},
        )
