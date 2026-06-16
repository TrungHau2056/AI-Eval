# AI Test Case Generator

Công cụ sinh test case tự động giúp AI Product Researcher đánh giá chất lượng phản hồi của AI/Chatbot. Thay vì đọc hàng nghìn comment thủ công, hệ thống dùng LLM để phân tích raw data → trích Intent → tạo Persona → sinh Test Prompt, với người dùng kiểm soát chất lượng ở mỗi bước.

## Kiến trúc

```
┌─────────────┐     REST API      ┌──────────────────┐
│  Frontend   │ ◄──────────────► │  FastAPI Backend  │
│  (React/...) │                   │                  │
└─────────────┘                   │  src/pipeline/   │
                                  │  src/llm/        │
                                  │  src/ingestion/  │
                                  └──────────────────┘
```

```
Raw Data → Intent Extraction → Persona Generation → Test Prompt Generation → Export
              (Bước 1)              (Bước 2)              (Bước 3)
           [review/edit]         [review/edit]          [review/edit]
```

**Nguyên lý cốt lõi: Human-in-the-loop.** AI sinh kết quả, con người duyệt/chỉnh sửa trước khi chuyển bước tiếp. Tránh ảo giác (hallucination) của LLM.

## Cấu trúc thư mục

```
backend/
├── main.py                      # FastAPI entry point
├── requirements.txt
├── pytest.ini
├── src/
│   ├── config.py                # Settings (API keys, chunking config) — đọc từ .env
│   ├── models/
│   │   └── schemas.py           # Pydantic models: Intent, Persona, TestCasePrompt, RawInput, PipelineState
│   ├── api/
│   │   ├── deps.py              # In-memory PipelineState singleton + reset
│   │   └── routers/
│   │       ├── input.py         # POST /api/input/text, /api/input/csv
│   │       ├── intents.py       # CRUD + extract + approve + regenerate
│   │       ├── personas.py      # CRUD + generate + approve + regenerate
│   │       ├── prompts.py       # CRUD + generate + regenerate
│   │       ├── export.py        # GET /api/export/csv, /api/export/markdown
│   │       └── state.py         # GET /api/state, POST /api/state/reset
│   ├── ingestion/
│   │   ├── base.py              # Abstract DataIngestion — interface mở rộng cho crawl/form
│   │   ├── csv_loader.py        # Đọc CSV, gộp cột text thành raw content
│   │   └── text_loader.py       # Nhận text paste trực tiếp
│   ├── llm/
│   │   ├── base.py              # Abstract LLMClient — generate() và generate_structured()
│   │   ├── gemini_client.py     # Google Gemini 1.5 Pro
│   │   ├── openai_client.py     # OpenAI GPT-4o
│   │   └── factory.py           # create_llm_client(model, api_key) → chọn implementation
│   ├── pipeline/
│   │   ├── intent_extractor.py  # Bước 1: Chunk text → gọi LLM → parse JSON → list[Intent]
│   │   ├── persona_generator.py # Bước 2: Intent → 2 Persona (easy + hard)
│   │   └── test_prompt_generator.py # Bước 3: Intent+Persona → Test Prompt
│   ├── prompts/
│   │   └── templates.py         # System/User prompt templates cho 3 bước pipeline
│   ├── chunking/
│   │   └── text_chunker.py      # Chia text dài theo sentence boundary, có overlap
│   └── export/
│       └── exporter.py          # Export to_csv() / to_markdown()
└── tests/                       # 19 unit tests

frontend/                        # Frontend code (tự gen)
├── src/
│   ├── api/                     # API client gọi backend
│   ├── components/              # Reusable UI components
│   └── pages/                   # Các trang theo bước pipeline
└── README.md                    # API endpoints reference

requirements.txt                 # Root-level dependencies
.env.example                     # Template API keys
```

## API Endpoints

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/api/input/text` | Paste text đầu vào |
| POST | `/api/input/csv` | Upload CSV đầu vào |
| POST | `/api/intents/extract` | Chạy LLM sinh Intent |
| GET | `/api/intents` | Lấy danh sách Intent |
| PUT | `/api/intents` | Cập nhật Intent (edit/delete) |
| POST | `/api/intents/approve` | Chốt Intent → chuyển bước 2 |
| POST | `/api/intents/regenerate` | Regenerate Intent + guidance |
| POST | `/api/personas/generate` | Chạy LLM sinh Persona |
| GET | `/api/personas` | Lấy danh sách Persona |
| PUT | `/api/personas` | Cập nhật Persona |
| POST | `/api/personas/approve` | Chốt Persona → chuyển bước 3 |
| POST | `/api/personas/regenerate` | Regenerate Persona + guidance |
| POST | `/api/prompts/generate` | Chạy LLM sinh Test Prompt |
| GET | `/api/prompts` | Lấy danh sách Test Prompt |
| PUT | `/api/prompts` | Cập nhật Test Prompt |
| POST | `/api/prompts/regenerate` | Regenerate Test Prompt + guidance |
| GET | `/api/export/csv` | Export CSV |
| GET | `/api/export/markdown` | Export Markdown |
| GET | `/api/state` | Lấy trạng thái pipeline hiện tại |
| POST | `/api/state/reset` | Reset toàn bộ pipeline |

API docs tự động: `http://localhost:8000/docs` (Swagger UI)

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

Mỗi bước có **Regenerate** với guidance text từ user, và **editable table** để sửa/xóa/thêm trước khi chốt.

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

pip install -r backend/requirements.txt
cp .env.example .env            # Điền API keys

# Chạy backend
cd backend
uvicorn main:app --reload --port 8000

# Frontend — xem frontend/README.md
```
