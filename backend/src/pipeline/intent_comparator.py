"""Gom cụm ngữ nghĩa intent đa nguồn (Gap Analysis, một bước duy nhất).

Hợp nhất data + prd → cluster theo ngữ nghĩa (hybrid: embedding lọc nhanh →
vùng xám đẩy 1 LLM-pass chấm "cùng intent?"). Mỗi cụm = 1 intent đại diện:
- source = mảng các nguồn đóng góp (vd ["data","prd"]).
- coverage suy từ source: cả prd&data → confirmed; chỉ prd → prd_only; chỉ data → data_only.
Bước này thay cả dedup trong-nguồn lẫn so khớp chéo PRD↔data (không cần so 2 lần).
"""
import json
import logging
from typing import Any

import numpy as np

from src.config import settings
from src.llm.base import LLMClient

logger = logging.getLogger(__name__)


def embed(texts: list[str], api_key: str, model: str = "") -> np.ndarray:
    """Embed list text bằng Gemini text-embedding. Trả ma trận (n, dim)."""
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = model or settings.embedding_model
    vectors: list[list[float]] = []
    # Gemini embed_content nhận từng content; lặp để tránh giới hạn batch.
    for t in texts:
        res = genai.embed_content(model=model, content=t or " ")
        vectors.append(res["embedding"])
    return np.array(vectors, dtype=float)


def _cosine_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    if a.size == 0 or b.size == 0:
        return np.zeros((len(a), len(b)))
    a_norm = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-9)
    b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-9)
    return a_norm @ b_norm.T


def _intent_text(it: dict[str, Any]) -> str:
    return " ".join(
        str(it.get(k, "")) for k in ("intent_name", "utterance", "moment")
    ).strip()


def _sources_of(it: dict[str, Any]) -> list[str]:
    """Chuẩn hoá source về list (tương thích cả dữ liệu cũ dạng scalar)."""
    s = it.get("source")
    if isinstance(s, list):
        return [x for x in s if x]
    if isinstance(s, str) and s:
        return [s]
    return []


_CLUSTER_SYSTEM = (
    "Bạn là chuyên gia phân tích intent. Với mỗi cặp (A, B), xác định A và B có CÙNG "
    "một intent người dùng hay không. Văn phong có thể lệch (formal vs chat viết tắt) "
    "nhưng cùng mục tiêu thì coi là cùng intent. "
    'Trả về JSON: {"results": [{"pair": <số>, "same": true/false}, ...]} và không thêm text nào khác.'
)


class _UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


async def _judge_same(
    llm: LLMClient, intents: list[dict], pairs: list[tuple[int, int]]
) -> list[bool]:
    """LLM chấm từng cặp vùng xám có cùng intent không. Lỗi → mặc định không gộp."""
    lines = []
    for idx, (i, j) in enumerate(pairs):
        a = intents[i].get("intent_name", "")
        a_utt = intents[i].get("utterance", "")
        b = intents[j].get("intent_name", "")
        b_utt = intents[j].get("utterance", "")
        lines.append(f'{idx}. A="{a}" / "{a_utt}" | B="{b}" / "{b_utt}"')
    prompt = "Các cặp cần chấm:\n" + "\n".join(lines)
    verdicts = [False] * len(pairs)
    try:
        raw = (await llm.generate(prompt, system_prompt=_CLUSTER_SYSTEM)).strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            raw = raw.rsplit("```", 1)[0]
        data = json.loads(raw.strip())
        for r in data.get("results", []):
            pi = r.get("pair")
            if isinstance(pi, int) and 0 <= pi < len(verdicts):
                verdicts[pi] = bool(r.get("same"))
    except Exception as e:
        logger.warning("Cluster gray-zone LLM judge failed, default không gộp: %s", e)
    return verdicts


def _coverage_for(sources: list[str], has_prd: bool, has_data: bool) -> str:
    """Suy coverage từ tập nguồn của cụm. Single-source run (chỉ 1 loại nguồn
    toàn cục) → "" (standalone, không gán nhãn gap)."""
    if not (has_prd and has_data):
        return ""
    s = set(sources)
    if "prd" in s and "data" in s:
        return "confirmed"
    if "prd" in s:
        return "prd_only"
    return "data_only"


def _merge_cluster(members: list[dict], has_prd: bool, has_data: bool) -> dict:
    """Gộp các intent trong 1 cụm thành 1 đại diện.

    name/moment/phase ưu tiên bản prd (canonical); utterance ưu tiên bản data (chat thật).
    source = hợp các nguồn; memberIds = mọi id gốc.
    """
    prd_member = next((m for m in members if "prd" in _sources_of(m)), None)
    data_member = next((m for m in members if "data" in _sources_of(m)), None)
    canonical = prd_member or members[0]
    utter_src = data_member or members[0]

    sources = sorted({s for m in members for s in _sources_of(m)})
    merged = dict(canonical)
    merged["source"] = sources
    merged["utterance"] = utter_src.get("utterance", "") or canonical.get("utterance", "")
    merged["memberIds"] = [m.get("id", "") for m in members]
    merged["coverage"] = _coverage_for(sources, has_prd, has_data)
    return merged


def _passthrough(intents: list[dict], has_prd: bool, has_data: bool) -> list[dict]:
    """Không gom cụm: chuẩn hoá source thành list + gán coverage single. Mỗi intent 1 dòng."""
    out = []
    for it in intents:
        m = dict(it)
        m["source"] = _sources_of(it)
        m["memberIds"] = [it.get("id", "")]
        m["coverage"] = _coverage_for(m["source"], has_prd, has_data)
        out.append(m)
    return out


async def cluster_intents(
    intents: list[dict],
    llm: LLMClient,
    api_key: str,
    embedding_model: str = "",
    high: float | None = None,
    low: float | None = None,
) -> list[dict]:
    """Gom cụm ngữ nghĩa toàn bộ intent (data + prd) → list intent đã gộp.

    Mỗi input nên đã gắn source dạng list (["data"]/["prd"]). Trả về intent đã
    gắn source (mảng) + coverage + memberIds.
    """
    high = settings.match_high if high is None else high
    low = settings.match_low if low is None else low

    has_prd = any("prd" in _sources_of(it) for it in intents)
    has_data = any("data" in _sources_of(it) for it in intents)

    if len(intents) < 2:
        return _passthrough(intents, has_prd, has_data)

    try:
        vecs = embed(
            [_intent_text(i) for i in intents],
            api_key,
            embedding_model or settings.embedding_model,
        )
        sim = _cosine_matrix(vecs, vecs)

        uf = _UnionFind(len(intents))
        gray_pairs: list[tuple[int, int]] = []
        for i in range(len(intents)):
            for j in range(i + 1, len(intents)):
                s = sim[i, j]
                if s >= high:
                    uf.union(i, j)
                elif s > low:
                    gray_pairs.append((i, j))

        if gray_pairs:
            verdicts = await _judge_same(llm, intents, gray_pairs)
            for (i, j), same in zip(gray_pairs, verdicts):
                if same:
                    uf.union(i, j)

        clusters: dict[int, list[dict]] = {}
        for idx, it in enumerate(intents):
            clusters.setdefault(uf.find(idx), []).append(it)

        return [_merge_cluster(members, has_prd, has_data) for members in clusters.values()]
    except Exception as e:
        # Embedding/LLM lỗi → không cụm, trả mỗi intent 1 dòng (degrade, không mất intent).
        logger.warning("cluster_intents degrade (bỏ gom cụm): %s", e)
        return _passthrough(intents, has_prd, has_data)
