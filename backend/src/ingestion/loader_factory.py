import io
import os

from src.ingestion.base import DataIngestion
from src.ingestion.csv_loader import CSVLoader
from src.ingestion.excel_loader import ExcelLoader
from src.ingestion.json_loader import JsonLoader
from src.ingestion.markdown_loader import MarkdownLoader
from src.ingestion.prd_loader import PRDLoader
from src.ingestion.social_loader import SocialLoader
from src.ingestion.text_loader import TextLoader

# Map đuôi file → loader class (cho data file dạng uploaded_file)
_EXT_LOADERS: dict[str, type[DataIngestion]] = {
    ".csv": CSVLoader,
    ".xlsx": ExcelLoader,
    ".xls": ExcelLoader,
    ".json": JsonLoader,
    ".jsonl": JsonLoader,
    ".md": MarkdownLoader,
    ".markdown": MarkdownLoader,
    ".txt": MarkdownLoader,
}


def get_loader(
    source_type: str | None = None,
    filename: str = "",
    uploaded_file: io.BytesIO | None = None,
    text: str = "",
) -> DataIngestion:
    """Chọn loader theo source_type (ưu tiên) hoặc đuôi file.

    - source_type="prd"   → PRDLoader (content + guidance)
    - source_type="text"  → TextLoader (paste tay)
    - source_type="social"→ SocialLoader (export Apify JSON/CSV)
    - còn lại             → suy từ đuôi file.
    """
    st = (source_type or "").lower()

    if st == "prd":
        return PRDLoader(uploaded_file, filename)
    if st == "text":
        return TextLoader(text)
    if st == "social":
        return SocialLoader(uploaded_file, filename)

    ext = os.path.splitext(filename)[1].lower()
    loader_cls = _EXT_LOADERS.get(ext)
    if loader_cls is None:
        raise ValueError(f"Định dạng không hỗ trợ: '{ext or filename}'")
    return loader_cls(uploaded_file, filename)
