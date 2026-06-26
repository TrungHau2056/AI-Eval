import io

import pandas as pd

from src.ingestion.base import DataIngestion
from src.models.schemas import RawInput


class ExcelLoader(DataIngestion):
    """Đọc file xlsx (pandas + openpyxl), gộp cột text như CSVLoader."""

    def __init__(self, uploaded_file: io.BytesIO, filename: str = ""):
        self.uploaded_file = uploaded_file
        self.filename = filename

    def load(self) -> RawInput:
        df = pd.read_excel(self.uploaded_file, engine="openpyxl")
        text_columns = df.select_dtypes(include=["object"]).columns.tolist()
        if not text_columns:
            raise ValueError("Excel không chứa cột text nào")
        rows = []
        for _, row in df[text_columns].iterrows():
            line = " | ".join(str(v) for v in row if pd.notna(v))
            if line.strip():
                rows.append(line)
        content = "\n---\n".join(rows)
        return RawInput(
            source_type="survey",
            content=content,
            metadata={"filename": self.filename, "columns": text_columns, "rows": len(df)},
        )
