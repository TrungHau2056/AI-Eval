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


def _pdf_bytes(text: str) -> bytes:
    import pytest

    fitz = pytest.importorskip("fitz")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    raw = doc.tobytes()
    doc.close()
    return raw


def test_ingest_survey_and_prd():
    reset_state()
    files = [
        ("files", ("sample_survey.xlsx", _fixture_bytes("sample_survey.xlsx"),
                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
        ("files", ("sample_prd.md", _fixture_bytes("sample_prd.md"), "text/markdown")),
    ]
    data = {"types": ["survey", "prd"]}
    res = client.post("/api/ingest", files=files, data=data)
    assert res.status_code == 200
    body = res.json()
    assert body["prd_loaded"] is True
    assert any(s["source_type"] == "survey" and s["status"] == "ok" for s in body["sources"])
    assert body["total_chars"] > 0

    state = get_state()
    assert "lái thử" in state.raw_input.content
    assert "Đặt lịch lái thử" in state.raw_prd_content


def test_ingest_empty_file_skipped():
    reset_state()
    empty = pd.DataFrame({"rating": [1, 2]})  # không có cột text
    buf = io.BytesIO()
    empty.to_excel(buf, index=False, engine="openpyxl")
    files = [("files", ("empty.xlsx", buf.getvalue(),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))]
    data = {"types": ["survey"]}
    res = client.post("/api/ingest", files=files, data=data)
    # Tất cả file skip → 400
    assert res.status_code == 400


def test_ingest_social_json():
    reset_state()
    files = [("files", ("data.json", _fixture_bytes("sample_apify_facebook.json"), "application/json"))]
    data = {"types": ["social"]}
    res = client.post("/api/ingest", files=files, data=data)
    assert res.status_code == 200
    body = res.json()
    assert any(s["source_type"] == "social" and s["status"] == "ok" for s in body["sources"])

    state = get_state()
    assert "Kia Morning" in state.raw_input.content
    assert "[social:facebook]" in state.raw_input.content


def test_ingest_pdf_text():
    reset_state()
    files = [("files", ("notes.pdf", _pdf_bytes("Refund policy and booking changes"), "application/pdf"))]
    data = {"types": ["text"]}
    res = client.post("/api/ingest", files=files, data=data)
    assert res.status_code == 200
    body = res.json()
    assert any(s["source_type"] == "text" and s["status"] == "ok" for s in body["sources"])

    state = get_state()
    assert "Refund policy" in state.raw_input.content


def test_prd_preview_after_pdf_ingest():
    reset_state()
    files = [("prd_file", ("prd.pdf", _pdf_bytes("Travel assistant PRD requirements"), "application/pdf"))]
    res = client.post("/api/ingest", files=files)
    assert res.status_code == 200

    preview = client.get("/api/prd/preview").json()
    assert preview["loaded"] is True
    assert preview["filename"] == "prd.pdf"
    assert preview["metadata"]["filetype"] == "pdf"
    assert "Travel assistant" in preview["content"]
    assert "Travel assistant" in preview["preview"]


def test_prd_upload_endpoint_and_preview():
    reset_state()
    files = {"prd_file": ("prd.pdf", _pdf_bytes("Standalone PRD upload"), "application/pdf")}
    res = client.post("/api/prd/upload", files=files)
    assert res.status_code == 200
    body = res.json()
    assert body["prd_loaded"] is True
    assert body["filename"] == "prd.pdf"

    preview = client.get("/api/prd/preview").json()
    assert preview["loaded"] is True
    assert "Standalone PRD" in preview["content"]


def test_ingest_ignores_swagger_empty_files_field():
    reset_state()
    files = [("prd_file", ("prd.pdf", _pdf_bytes("Swagger PRD upload"), "application/pdf"))]
    res = client.post("/api/ingest", files=files, data={"files": "", "types": ""})
    assert res.status_code == 200
    body = res.json()
    assert body["prd_loaded"] is True

    preview = client.get("/api/prd/preview").json()
    assert "Swagger PRD upload" in preview["content"]


def test_ingest_then_skip_warns_but_keeps_valid():
    reset_state()
    files = [
        ("files", ("sample_survey.xlsx", _fixture_bytes("sample_survey.xlsx"),
                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
        ("files", ("sample_corrupt.json", _fixture_bytes("sample_corrupt.json"), "application/json")),
    ]
    data = {"types": ["survey", "survey"]}
    res = client.post("/api/ingest", files=files, data=data)
    assert res.status_code == 200
    body = res.json()
    assert any(s["status"] == "skipped" for s in body["sources"])
    assert body["warnings"]
