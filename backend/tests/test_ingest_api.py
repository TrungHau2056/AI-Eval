import io
import os

import pandas as pd
from fastapi.testclient import TestClient

from main import app
from src.api.deps import get_state, reset_state

client = TestClient(app)
FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _fixture_bytes(name: str) -> bytes:
    with open(os.path.join(FIXTURES, name), "rb") as f:
        return f.read()


def test_ingest_survey_and_prd():
    reset_state()
    files = [
        ("files", ("sample_survey.xlsx", _fixture_bytes("sample_survey.xlsx"),
                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
        ("prd_file", ("sample_prd.md", _fixture_bytes("sample_prd.md"), "text/markdown")),
    ]
    res = client.post("/api/ingest", files=files)
    assert res.status_code == 200
    body = res.json()
    assert body["prd_loaded"] is True
    assert any(s["source_type"] == "survey" and s["status"] == "ok" for s in body["sources"])
    assert body["total_chars"] > 0

    state = get_state()
    assert "lái thử" in state.raw_input.content
    assert "Đặt lịch lái thử" in state.raw_prd_content


def test_ingest_md_txt_as_document():
    """File .md/.txt nạp vào vùng upload (không cần chọn loại nguồn) → đọc làm raw data."""
    reset_state()
    files = [
        ("files", ("note.md", "# Tiêu đề\nKhách hỏi cách đặt lịch lái thử xe".encode("utf-8"),
                   "text/markdown")),
        ("files", ("log.txt", "Tôi muốn hủy vé đã đặt nhưng không thấy nút".encode("utf-8"),
                   "text/plain")),
    ]
    res = client.post("/api/ingest", files=files)
    assert res.status_code == 200
    body = res.json()
    assert all(s["status"] == "ok" for s in body["sources"])
    assert body["total_chars"] > 0

    state = get_state()
    assert "đặt lịch lái thử" in state.raw_input.content
    assert "hủy vé" in state.raw_input.content


def test_ingest_empty_file_skipped():
    reset_state()
    empty = pd.DataFrame({"rating": [1, 2]})  # không có cột text
    buf = io.BytesIO()
    empty.to_excel(buf, index=False, engine="openpyxl")
    files = [("files", ("empty.xlsx", buf.getvalue(),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))]
    res = client.post("/api/ingest", files=files)
    # Tất cả file skip → 400
    assert res.status_code == 400


def test_ingest_social_json():
    """Social Apify JSON tự upload: định tuyến theo đuôi → JsonLoader vẫn bóc được text."""
    reset_state()
    files = [("files", ("data.json", _fixture_bytes("sample_apify_facebook.json"), "application/json"))]
    res = client.post("/api/ingest", files=files)
    assert res.status_code == 200
    body = res.json()
    assert any(s["source_type"] == "survey" and s["status"] == "ok" for s in body["sources"])

    state = get_state()
    assert "Kia Morning" in state.raw_input.content
    assert "[survey:data.json]" in state.raw_input.content


def test_ingest_then_skip_warns_but_keeps_valid():
    reset_state()
    files = [
        ("files", ("sample_survey.xlsx", _fixture_bytes("sample_survey.xlsx"),
                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
        ("files", ("sample_corrupt.json", _fixture_bytes("sample_corrupt.json"), "application/json")),
    ]
    res = client.post("/api/ingest", files=files)
    assert res.status_code == 200
    body = res.json()
    assert any(s["status"] == "skipped" for s in body["sources"])
    assert body["warnings"]
