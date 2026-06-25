import re

from src.models.schemas import RawInput

_HTML_TAG = re.compile(r"<[^>]+>")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_WS = re.compile(r"[ \t]+")

# Tách content theo separator nội bộ của loader ("\n---\n").
_RECORD_SEP = re.compile(r"\n-{3,}\n")


def _clean_line(line: str) -> str:
    line = _HTML_TAG.sub(" ", line)
    line = _CONTROL.sub("", line)
    line = _WS.sub(" ", line)
    return line.strip()


def normalize(
    lines: list[str],
    min_words: int = 3,
    min_chars: int = 10,
    lang_filter: bool = False,
    keep_lang: str = "vi",
) -> list[str]:
    """Lọc nhiễu cơ bản theo TechSpec §7:
    1. strip whitespace/control/HTML tag.
    2. bỏ dòng < min_words từ HOẶC < min_chars ký tự.
    3. dedup exact (case-insensitive) giữ bản đầu.
    4. (optional) lọc ngôn ngữ giữ keep_lang; confidence thấp → giữ lại (NFR5).
    """
    seen: set[str] = set()
    result: list[str] = []
    for raw in lines:
        line = _clean_line(raw)
        if not line:
            continue
        if len(line.split()) < min_words and len(line) < min_chars:
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        if lang_filter and not _keep_language(line, keep_lang):
            continue
        result.append(line)
    return result


def _keep_language(line: str, keep_lang: str) -> bool:
    """Trả True nếu giữ dòng. Confidence thấp/không chắc → giữ lại (tránh loại nhầm)."""
    try:
        from langdetect import DetectorFactory, detect_langs

        DetectorFactory.seed = 0
        langs = detect_langs(line)
        if not langs:
            return True
        top = langs[0]
        # Đúng ngôn ngữ → giữ; sai nhưng confidence < 0.7 → vẫn giữ (câu chêm tiếng Anh).
        if top.lang == keep_lang:
            return True
        return top.prob < 0.7
    except Exception:
        return True


def _split_records(content: str) -> list[str]:
    return [r for r in _RECORD_SEP.split(content) if r.strip()]


def _source_label(ri: RawInput) -> str:
    platform = ri.metadata.get("platform")
    filename = ri.metadata.get("filename")
    detail = platform or filename or ""
    return f"{ri.source_type}:{detail}" if detail else ri.source_type


# Ưu tiên thứ tự nguồn khi gộp (social → survey → text).
_SOURCE_ORDER = {"social": 0, "survey": 1, "text": 2}


def merge_sources(
    inputs: list[RawInput],
    min_words: int = 3,
    lang_filter: bool = False,
) -> RawInput:
    """Gộp CHỈ data thật (social/survey/text) vào 1 RawInput.content với nhãn nguồn.
    PRD KHÔNG được merge ở đây (giữ tách biệt để đối chiếu).
    """
    data_inputs = [ri for ri in inputs if ri.source_type != "prd"]
    data_inputs.sort(key=lambda ri: _SOURCE_ORDER.get(ri.source_type, 99))

    blocks: list[str] = []
    total_rows = 0
    for ri in data_inputs:
        records = _split_records(ri.content)
        cleaned = normalize(records, min_words=min_words, lang_filter=lang_filter)
        if not cleaned:
            continue
        total_rows += len(cleaned)
        label = _source_label(ri)
        body = "\n".join(cleaned)
        blocks.append(f"\n---[{label}]---\n{body}")

    content = "\n".join(blocks).strip()
    return RawInput(
        source_type="merged",
        content=content,
        metadata={"sources": len(blocks), "rows": total_rows},
    )
