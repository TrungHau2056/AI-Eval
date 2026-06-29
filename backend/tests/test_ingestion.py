import asyncio
import io
import os

import numpy as np
import pytest

from src.ingestion.excel_loader import ExcelLoader
from src.ingestion.json_loader import JsonLoader
from src.ingestion.loader_factory import get_loader
from src.ingestion.markdown_loader import MarkdownLoader
from src.ingestion.normalizer import merge_sources, normalize
from src.ingestion.prd_loader import PRDLoader
from src.ingestion.social_loader import SocialLoader
from src.models.schemas import RawInput
from src.pipeline import intent_comparator
from src.pipeline.intent_comparator import IntentComparator

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _open(name: str) -> io.BytesIO:
    with open(os.path.join(FIXTURES, name), "rb") as f:
        return io.BytesIO(f.read())


# ---------- Loaders ----------


def test_excel_loader():
    result = ExcelLoader(_open("sample_survey.xlsx"), "sample_survey.xlsx").load()
    assert result.source_type == "survey"
    assert "lái thử" in result.content
    assert result.metadata["filename"] == "sample_survey.xlsx"


def test_json_loader_whitelist_and_nested():
    result = JsonLoader(_open("sample_social.json"), "sample_social.json").load()
    assert "sạc ở đâu vậy mn ơi" in result.content
    assert "trạm sạc gần đây chỗ nào nhỉ" in result.content
    # nested message key được duyệt đệ quy
    assert "xuất hoá đơn điện tử kiểu gì v" in result.content


def test_json_loader_corrupt_raises():
    with pytest.raises(Exception):
        JsonLoader(_open("sample_corrupt.json"), "sample_corrupt.json").load()


def test_markdown_loader_keeps_raw():
    # Giữ NGUYÊN VĂN: ký hiệu markdown không bị strip.
    result = MarkdownLoader(_open("sample_prd.md"), "sample_prd.md").load()
    assert "#" in result.content
    assert "Đặt lịch lái thử" in result.content


def test_loader_factory_by_extension():
    assert isinstance(get_loader(filename="a.xlsx", uploaded_file=_open("sample_survey.xlsx")), ExcelLoader)
    assert isinstance(get_loader(source_type="prd", filename="p.md", uploaded_file=_open("sample_prd.md")), PRDLoader)


def test_loader_factory_social():
    loader = get_loader(source_type="social", filename="data.json", uploaded_file=_open("sample_apify_facebook.json"))
    assert isinstance(loader, SocialLoader)


# ---------- SocialLoader (FR-A4) ----------


def test_social_loader_maps_apify_export():
    result = SocialLoader(_open("sample_apify_facebook.json"), "data.json").load()
    assert result.source_type == "social"
    assert result.metadata["platform"] == "facebook"
    # 3 record nhưng 1 record message rỗng → bị bỏ → còn 2
    assert result.metadata["rows"] == 2
    assert "mua xe chạy gia đình" in result.content
    assert "Kia Morning" in result.content
    # provenance giữ post_id/url/timestamp
    assert result.metadata["records"][0]["post_id"] == "2276025789823542"
    assert result.metadata["records"][0]["timestamp"].startswith("2026-")


def test_social_loader_empty_raises():
    with pytest.raises(ValueError, match="0 dòng text"):
        SocialLoader(io.BytesIO(b'[{"type":"post"}]'), "empty.json").load()


# ---------- PRDLoader ----------


def test_prd_loader_content():
    ri = PRDLoader(_open("sample_prd.md"), "sample_prd.md").load()
    assert ri.source_type == "prd"
    assert "Đặt lịch lái thử" in ri.content
    assert "#" in ri.content  # giữ nguyên văn markdown (không strip)


# ---------- Normalizer ----------


def test_normalize_dedup_and_minwords():
    lines = ["  Đặt lái thử VF8 cuối tuần  ", "đặt lái thử vf8 cuối tuần", "k", "Tìm trạm sạc gần đây nhất"]
    out = normalize(lines, min_words=3)
    assert out == ["Đặt lái thử VF8 cuối tuần", "Tìm trạm sạc gần đây nhất"]


def test_normalize_strips_html():
    out = normalize(["<p>câu hỏi có thẻ html đây</p>"], min_words=3)
    assert out == ["câu hỏi có thẻ html đây"]


def test_merge_sources_labels_and_excludes_prd():
    survey = RawInput(source_type="survey", content="đặt lái thử vf8 cuối tuần\n---\ntìm trạm sạc gần đây", metadata={"filename": "s.xlsx"})
    prd = RawInput(source_type="prd", content="nội dung prd không được merge ở đây")
    merged = merge_sources([survey, prd])
    assert "[survey:s.xlsx]" in merged.content
    assert "nội dung prd" not in merged.content


# ---------- IntentComparator ----------


class _MockLLM:
    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        return '{"results": []}'


def _fake_embed(texts, api_key, model=""):
    table = {"lái thử": [1, 0, 0], "hóa đơn": [0, 1, 0], "trạm sạc": [0, 0, 1]}
    out = []
    for t in texts:
        vec = [0.0, 0.0, 0.0]
        for key, v in table.items():
            if key in t:
                vec = v
        out.append(vec)
    return np.array(out, dtype=float)


def test_comparator_coverage(monkeypatch):
    monkeypatch.setattr(intent_comparator, "embed", _fake_embed)
    prd = [
        {"id": "p1", "intent_name": "Đặt lịch lái thử", "utterance": "", "moment": ""},
        {"id": "p2", "intent_name": "Xuất hóa đơn điện tử", "utterance": "", "moment": ""},
    ]
    data = [
        {"id": "d1", "intent_name": "đặt lái thử vf8 t7", "utterance": "", "moment": ""},
        {"id": "d2", "intent_name": "Báo trạm sạc hỏng", "utterance": "", "moment": ""},
    ]
    comparator = IntentComparator(_MockLLM(), api_key="x")
    prd_out, data_out = asyncio.run(comparator.compare(prd, data))

    by_id = {i["id"]: i for i in prd_out + data_out}
    assert by_id["p1"]["coverage"] == "confirmed"
    assert by_id["d1"]["coverage"] == "confirmed"
    assert by_id["d1"]["id"] in by_id["p1"]["matchedIds"]
    assert by_id["p2"]["coverage"] == "prd_only"
    assert by_id["d2"]["coverage"] == "data_only"


def test_comparator_degrades_on_embed_failure(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("404 model not found")

    monkeypatch.setattr(intent_comparator, "embed", _boom)
    prd = [{"id": "p1", "intent_name": "Đặt lịch lái thử", "utterance": "", "moment": ""}]
    data = [{"id": "d1", "intent_name": "đặt lái thử vf8", "utterance": "", "moment": ""}]
    comparator = IntentComparator(_MockLLM(), api_key="x")
    prd_out, data_out = asyncio.run(comparator.compare(prd, data))
    # Không sập; intent vẫn ra với source đúng, coverage rỗng.
    assert prd_out[0]["source"] == "prd" and prd_out[0]["coverage"] == ""
    assert data_out[0]["source"] == "data" and data_out[0]["coverage"] == ""


def test_comparator_standalone():
    prd = [{"id": "p1", "intent_name": "Đặt lịch lái thử", "utterance": "", "moment": ""}]
    comparator = IntentComparator(_MockLLM(), api_key="x")
    prd_out, data_out = asyncio.run(comparator.compare(prd, []))
    assert prd_out[0]["source"] == "prd"
    assert prd_out[0]["coverage"] == ""
    assert data_out == []
