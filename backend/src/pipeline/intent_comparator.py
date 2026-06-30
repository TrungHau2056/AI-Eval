"""IntentComparator — đối chiếu intent PRD ↔ data (Gap Analysis, FR-B5).

Hybrid: embedding lọc nhanh (cosine) → vùng xám đẩy 1 LLM-pass chấm "cùng intent?".
Gắn nhãn coverage ∈ {confirmed, prd_only, data_only} + matchedIds lên mỗi intent.
"""
import json
import logging
from typing import Any

import numpy as np

from src.config import settings
from src.llm.base import LLMClient

logger = logging.getLogger(__name__)


def embed(texts: list[str], api_key: str, model: str = "", provider: str = "gemini") -> np.ndarray:
    """Embed list text. Trả ma trận (n, dim). provider ∈ {gemini, openai}.

    Cùng provider+model cho cả 2 phía → cùng số chiều → cosine hợp lệ.
    """
    if provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        model = model or settings.openai_embedding_model
        # OpenAI embeddings nhận cả list trong 1 call.
        resp = client.embeddings.create(model=model, input=[t or " " for t in texts])
        vectors = [d.embedding for d in resp.data]
        return np.array(vectors, dtype=float)

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


_GRAY_SYSTEM = (
    "Bạn là chuyên gia phân tích intent. Với mỗi cặp (A từ PRD, B từ data thật), "
    "xác định A và B có CÙNG một intent người dùng hay không. "
    "Văn phong có thể lệch (PRD formal vs chat viết tắt) nhưng cùng mục tiêu thì coi là cùng intent. "
    'Trả về JSON: {"results": [{"pair": <số>, "same": true/false}, ...]} và không thêm text nào khác.'
)


class IntentComparator:
    def __init__(
        self,
        llm: LLMClient,
        api_key: str,
        embedding_model: str = "",
        high: float | None = None,
        low: float | None = None,
        provider: str = "gemini",
    ):
        self.llm = llm
        self.api_key = api_key
        self.provider = provider
        default_embed = settings.openai_embedding_model if provider == "openai" else settings.embedding_model
        self.embedding_model = embedding_model or default_embed
        self.high = settings.match_high if high is None else high
        self.low = settings.match_low if low is None else low

    async def compare(
        self, prd_intents: list[dict], data_intents: list[dict]
    ) -> tuple[list[dict], list[dict]]:
        """Annotate source + coverage + matchedIds lên 2 tập intent.

        Standalone (1 phía rỗng) → giữ source gốc, coverage="".
        """
        for it in prd_intents:
            if it.get("source") not in ("prd", "prd_inferred"):
                it["source"] = "prd"
        for it in data_intents:
            if it.get("source") != "data":
                it["source"] = "data"

        if not prd_intents or not data_intents:
            # Standalone: không đối chiếu.
            return self._no_comparison(prd_intents, data_intents)

        try:
            prd_vecs = embed([_intent_text(i) for i in prd_intents], self.api_key, self.embedding_model, self.provider)
            data_vecs = embed([_intent_text(i) for i in data_intents], self.api_key, self.embedding_model, self.provider)
            sim = _cosine_matrix(prd_vecs, data_vecs)

            matched = np.zeros_like(sim, dtype=bool)
            gray_pairs: list[tuple[int, int]] = []
            for i in range(sim.shape[0]):
                for j in range(sim.shape[1]):
                    s = sim[i, j]
                    if s >= self.high:
                        matched[i, j] = True
                    elif s > self.low:
                        gray_pairs.append((i, j))

            if gray_pairs:
                verdicts = await self._judge_gray(prd_intents, data_intents, gray_pairs)
                for (i, j), same in zip(gray_pairs, verdicts):
                    if same:
                        matched[i, j] = True

            self._apply_coverage(prd_intents, data_intents, matched)
        except Exception as e:
            # Embedding/LLM lỗi (404 model, hết quota, mạng...) → không sập discover,
            # chỉ bỏ cột Coverage (Fallback UX: không che, không crash).
            logger.warning("IntentComparator degrade (bỏ đối chiếu): %s", e)
            return self._no_comparison(prd_intents, data_intents)

        return prd_intents, data_intents

    @staticmethod
    def _no_comparison(prd_intents: list[dict], data_intents: list[dict]) -> tuple[list[dict], list[dict]]:
        for it in prd_intents + data_intents:
            it["coverage"] = ""
            it["matchedIds"] = []
        return prd_intents, data_intents

    async def _judge_gray(
        self, prd_intents: list[dict], data_intents: list[dict], pairs: list[tuple[int, int]]
    ) -> list[bool]:
        lines = []
        for idx, (i, j) in enumerate(pairs):
            a = prd_intents[i].get("intent_name", "")
            b = data_intents[j].get("intent_name", "")
            b_utt = data_intents[j].get("utterance", "")
            lines.append(f'{idx}. A(PRD)="{a}" | B(data)="{b}" / "{b_utt}"')
        prompt = "Các cặp cần chấm:\n" + "\n".join(lines)
        verdicts = [False] * len(pairs)
        try:
            raw = await self.llm.generate(prompt, system_prompt=_GRAY_SYSTEM)
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                raw = raw.rsplit("```", 1)[0]
            data = json.loads(raw.strip())
            for r in data.get("results", []):
                pi = r.get("pair")
                if isinstance(pi, int) and 0 <= pi < len(verdicts):
                    verdicts[pi] = bool(r.get("same"))
        except Exception as e:
            logger.warning("Gray-zone LLM judge failed, default không gộp: %s", e)
        return verdicts

    @staticmethod
    def _apply_coverage(prd_intents: list[dict], data_intents: list[dict], matched: np.ndarray) -> None:
        for i, it in enumerate(prd_intents):
            data_ids = [data_intents[j]["id"] for j in range(matched.shape[1]) if matched[i, j]]
            it["matchedIds"] = data_ids
            it["coverage"] = "confirmed" if data_ids else "prd_only"
        for j, it in enumerate(data_intents):
            prd_ids = [prd_intents[i]["id"] for i in range(matched.shape[0]) if matched[i, j]]
            it["matchedIds"] = prd_ids
            it["coverage"] = "confirmed" if prd_ids else "data_only"
