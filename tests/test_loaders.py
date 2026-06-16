import io

import pandas as pd
import pytest

from src.ingestion.csv_loader import CSVLoader
from src.ingestion.text_loader import TextLoader


def test_text_loader():
    loader = TextLoader("Hello world")
    result = loader.load()
    assert result.source_type == "text"
    assert result.content == "Hello world"


def test_text_loader_empty():
    loader = TextLoader("  ")
    with pytest.raises(ValueError, match="không được để trống"):
        loader.load()


def test_csv_loader():
    df = pd.DataFrame({"feedback": ["Good product", "Bad service"], "rating": [5, 1]})
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)

    loader = CSVLoader(buf, filename="test.csv")
    result = loader.load()
    assert result.source_type == "csv"
    assert "Good product" in result.content
    assert "Bad service" in result.content
    assert result.metadata["filename"] == "test.csv"


def test_csv_loader_no_text_columns():
    df = pd.DataFrame({"rating": [5, 1]})
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)

    loader = CSVLoader(buf, filename="test.csv")
    with pytest.raises(ValueError, match="không chứa cột text"):
        loader.load()
