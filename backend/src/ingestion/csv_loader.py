import io

import pandas as pd

from src.ingestion.base import DataIngestion
from src.models.schemas import RawInput


class CSVLoader(DataIngestion):
    def __init__(self, uploaded_file: io.BytesIO, filename: str = ""):
        self.uploaded_file = uploaded_file
        self.filename = filename

    def load(self) -> RawInput:
        df = pd.read_csv(self.uploaded_file)
        text_columns = df.select_dtypes(include=["object"]).columns.tolist()
        if not text_columns:
            raise ValueError("CSV không chứa cột text nào")
        rows = []
        for _, row in df[text_columns].iterrows():
            rows.append(" | ".join(str(v) for v in row if pd.notna(v)))
        content = "\n---\n".join(rows)
        return RawInput(
            source_type="csv",
            content=content,
            metadata={"filename": self.filename, "columns": text_columns, "rows": len(df)},
        )
