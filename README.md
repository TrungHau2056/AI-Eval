# AI Test Case Generator

Công cụ sinh test case tự động giúp AI Product Researcher đánh giá chất lượng phản hồi của AI/Chatbot. Thay vì đọc hàng nghìn comment thủ công, hệ thống dùng LLM để phân tích raw data → trích Intent → tạo Persona → sinh Test Prompt, với người dùng kiểm soát chất lượng ở mỗi bước.

## Kiến trúc

```
Raw Data → Intent Extraction → Persona Generation → Test Prompt Generation → Export
              (Bước 1)              (Bước 2)              (Bước 3)
           [review/edit]         [review/edit]          [review/edit]
```

**Nguyên lý cốt lõi: Human-in-the-loop.** AI sinh kết quả, con người duyệt/chỉnh sửa trước khi chuyển bước tiếp. Tránh ảo giác (hallucination) của LLM.

## Cấu trúc thư mục

```
app.py                          # Entry point Streamlit — toàn bộ UI flow 4 bước
requirements.txt
.env.example                    # Template API keys

src/
├── config.py                   # Settings (API keys, chunking config) — đọc từ .env
├── models/
│   └── schemas.py              # Pydantic models: Intent, Persona, TestCasePrompt, RawInput, PipelineState
├── ingestion/
│   ├── base.py                 # Abstract DataIngestion — interface mở rộng cho crawl/form sau này
│   ├── csv_loader.py           # Đọc CSV, gộp cột text thành raw content
│   └── text_loader.py          # Nhận text paste trực tiếp
├── llm/
│   ├── base.py                 # Abstract LLMClient — generate() và generate_structured()
│   ├── gemini_client.py        # Google Gemini 1.5 Pro (context window lớn, phù hợp text dài)
│   ├── openai_client.py        # OpenAI GPT-4o
│   └── factory.py              # create_llm_client(model, api_key) → chọn implementation
├── pipeline/
│   ├── intent_extractor.py     # Bước 1: Chunk text → gọi LLM → parse JSON → list[Intent]
│   ├── persona_generator.py    # Bước 2: Với mỗi Intent → gọi LLM → 2 Persona (easy + hard)
│   └── test_prompt_generator.py# Bước 3: Intent + Persona → gọi LLM → Test Prompt đóng vai
├── prompts/
│   └── templates.py            # System/User prompt templates cho 3 bước pipeline
├── chunking/
│   └── text_chunker.py         # Chia text dài theo sentence boundary, có overlap
└── export/
    └── exporter.py             # Export to_csv() / to_markdown() — grouped by Intent → Persona

tests/                          # 19 unit tests (schemas, loaders, chunker, pipeline parse, export)
```

## Data Models

| Model | Vai trò | Key fields |
|---|---|---|
| `Intent` | Bối cảnh + Mục tiêu người dùng | `context`, `goal`, `evidence[]` (internal — trích dẫn gốc hỗ trợ intent, không hiện UI) |
| `Persona` | Nhân vật đóng vai test | `intent_id` (FK), `name`, `description`, `trait_type` (easy/hard) |
| `TestCasePrompt` | Prompt cuối cùng để test AI | `persona_id` (FK), `intent_id` (FK), `prompt_text` |
| `RawInput` | Dữ liệu đầu vào | `source_type` (csv/text/crawl), `content` |
| `PipelineState` | Trạng thái toàn pipeline | `raw_input`, `intents[]`, `personas[]`, `test_prompts[]`, `current_step` |

## Pipeline chi tiết

### Bước 1: Intent Extraction
- **Input:** RawInput (raw text từ CSV hoặc paste)
- **Process:** Text chunker chia nhỏ nếu quá dài → gọi LLM với prompt trích Intent → parse JSON response → deduplicate
- **Output:** `list[Intent]` — mỗi Intent có context, goal, evidence (quotes gốc)
- **Evidence** không hiện trên UI, chỉ dùng internally để LLM hiểu ngữ cảnh tốt hơn ở bước sau

### Bước 2: Persona Generation
- **Input:** `list[Intent]` đã duyệt
- **Process:** Với mỗi Intent, gọi LLM sinh 2 persona trái ngược (easy: hợp tác/rõ ràng, hard: thiếu kiên nhẫn/mơ hồ). Kèm evidence của Intent.
- **Output:** `list[Persona]` — 2 persona mỗi intent

### Bước 3: Test Prompt Generation
- **Input:** `list[Intent]` + `list[Persona]` đã duyệt
- **Process:** Với mỗi Persona, gọi LLM viết prompt đóng vai, phản ánh đúng context/goal và tính cách persona
- **Output:** `list[TestCasePrompt]`

Mỗi bước có **Regenerate** với guidance text từ user, và **editable table** (`st.data_editor`) để sửa/xóa/thêm trước khi chốt.

## LLM Abstraction

```python
class LLMClient(ABC):
    async def generate(prompt, system_prompt="") -> str
    async def generate_structured(prompt, schema, system_prompt="") -> BaseModel
```

- `generate_structured` gửi JSON schema cho LLM, parse response thành Pydantic model
- Cả Gemini và OpenAI đều strip markdown code fences nếu LLM bọc JSON trong ```
- Factory pattern: `create_llm_client("gemini", api_key)` hoặc `create_llm_client("openai", api_key)`

## Text Chunking

Khi text đầu vào vượt `chunk_max_tokens` (default: 50K tokens ~ 200K chars):
1. Chia theo sentence boundary (không cắt giữa câu)
2. Overlap nhỏ giữa các chunk (~500 tokens) để không mất ngữ cảnh
3. Mỗi chunk xử lý riêng, intents từ tất cả chunks được merge + deduplicate

## Data Ingestion

```python
class DataIngestion(ABC):
    def load(self) -> RawInput: ...
```

MVP implement `CSVLoader` và `TextLoader`. Interface này thiết kế sẵn để mở rộng `CrawlLoader`, `FormLoader` sau này mà không cần đổi pipeline code.

## Cài đặt & Chạy

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac

pip install -r requirements.txt
cp .env.example .env            # Điền API keys

streamlit run app.py
```

## UI Flow (Streamlit)

1. **Sidebar:** Chọn model (Gemini/OpenAI) + nhập API Key
2. **Bước 0:** Upload CSV hoặc paste text → "Phân tích Intent"
3. **Bước 1:** Bảng Intent editable → sửa/xóa/regenerate → "Chốt Intent → Sinh Persona"
4. **Bước 2:** Bảng Persona editable → sửa/xóa/regenerate → "Chốt Persona → Sinh Test Prompt"
5. **Bước 3:** Bảng Test Prompt editable → Export CSV hoặc Markdown
