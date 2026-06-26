import io

import pandas as pd

from src.ingestion.base import DataIngestion
from src.ingestion.json_loader import JsonLoader
from src.models.schemas import RawInput

# Field nguồn theo thứ tự ưu tiên → tên đích. Verify với export Apify Facebook thật;
# fallback các tên field actor khác (tiktok/threads) để pluggable (NFR1).
_TEXT_KEYS = ["message", "text", "commentText", "content", "caption"]
_POST_ID_KEYS = ["post_id", "postId", "id"]
_URL_KEYS = ["url", "videoUrl", "postUrl"]
_TIME_KEYS = ["date", "createTimeISO", "timestamp", "time"]
_AUTHOR_KEYS = ["ownerUsername", "author", "username"]


def _first(record: dict, keys: list[str]):
    for k in keys:
        v = record.get(k)
        if v not in (None, ""):
            return v
    return None


def _author(record: dict):
    # authorMeta.name (nested) → các key phẳng
    meta = record.get("authorMeta")
    if isinstance(meta, dict) and meta.get("name"):
        return meta["name"]
    return _first(record, _AUTHOR_KEYS)


def _platform_from_url(url: str | None) -> str:
    if not url:
        return "unknown"
    u = url.lower()
    if "facebook.com" in u or "fb.com" in u or "fb.watch" in u:
        return "facebook"
    if "tiktok.com" in u:
        return "tiktok"
    if "threads.net" in u or "threads.com" in u:
        return "threads"
    if "instagram.com" in u:
        return "instagram"
    return "unknown"


class SocialLoader(DataIngestion):
    """Đọc export Apify (JSON/CSV) cho social (fb/tiktok/threads).

    Mỗi record → 1 utterance (field text) + provenance vào metadata.records.
    `content` (gộp utterance) là cái LLM ăn; provenance là bonus optional (NFR2).
    """

    def __init__(self, uploaded_file: io.BytesIO, filename: str = ""):
        self.uploaded_file = uploaded_file
        self.filename = filename

    def _read_records(self) -> list[dict]:
        if self.filename.lower().endswith(".csv"):
            df = pd.read_csv(self.uploaded_file)
            return df.to_dict(orient="records")
        # JSON/JSONL: tái dùng parser robust của JsonLoader
        raw = self.uploaded_file.read()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        data = JsonLoader(io.BytesIO(b""), self.filename)._parse(raw)
        if isinstance(data, dict):
            # cho phép {"data": [...]} hoặc 1 object đơn
            for key in ("data", "items", "results", "posts", "comments"):
                if isinstance(data.get(key), list):
                    return data[key]
            return [data]
        if isinstance(data, list):
            return [r for r in data if isinstance(r, dict)]
        return []

    def load(self) -> RawInput:
        records = self._read_records()
        utterances: list[str] = []
        provenance: list[dict] = []
        platform = "unknown"

        for rec in records:
            if not isinstance(rec, dict):
                continue
            text = _first(rec, _TEXT_KEYS)
            if not text or not str(text).strip():
                continue  # thiếu text → bỏ record
            utterances.append(str(text).strip())

            url = _first(rec, _URL_KEYS)
            if platform == "unknown":
                platform = _platform_from_url(url)
            prov = {
                "post_id": _first(rec, _POST_ID_KEYS),
                "url": url,
                "timestamp": _first(rec, _TIME_KEYS),
                "author": _author(rec),
                "reactions_count": rec.get("reactions_count"),
                "comments_count": rec.get("comments_count"),
            }
            provenance.append({k: v for k, v in prov.items() if v is not None})

        if not utterances:
            raise ValueError("File social: 0 dòng text hợp lệ")

        content = "\n---\n".join(utterances)
        return RawInput(
            source_type="social",
            content=content,
            metadata={
                "filename": self.filename,
                "platform": platform,
                "rows": len(utterances),
                "records": provenance,
            },
        )
