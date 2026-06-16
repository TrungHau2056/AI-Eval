import re


def _estimate_tokens(text: str) -> int:
    return len(text) // 4


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r'(?<=[.!?。！？])\s+', text)
    return [p.strip() for p in parts if p.strip()]


def chunk_text(text: str, max_tokens: int = 50000, overlap_tokens: int = 500) -> list[str]:
    if _estimate_tokens(text) <= max_tokens:
        return [text]

    sentences = _split_sentences(text)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        sent_tokens = _estimate_tokens(sentence)
        if current_len + sent_tokens > max_tokens and current:
            chunks.append(" ".join(current))
            overlap_text = " ".join(current)
            overlap_sent = _split_sentences(overlap_text)
            overlap_chunk: list[str] = []
            overlap_len = 0
            for s in reversed(overlap_sent):
                s_tokens = _estimate_tokens(s)
                if overlap_len + s_tokens > overlap_tokens:
                    break
                overlap_chunk.insert(0, s)
                overlap_len += s_tokens
            current = overlap_chunk
            current_len = _estimate_tokens(" ".join(current))
        current.append(sentence)
        current_len += sent_tokens

    if current:
        chunks.append(" ".join(current))

    return chunks
