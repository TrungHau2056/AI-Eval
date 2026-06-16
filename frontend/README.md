# Frontend

Folder này chứa source code frontend cho AI Test Case Generator.

## Cấu trúc đề xuất

```
frontend/
├── public/
├── src/
│   ├── api/              # API client gọi backend FastAPI
│   │   └── client.ts     # Base fetch wrapper + endpoints
│   ├── components/       # Reusable components
│   │   ├── IntentTable.tsx       # Bảng editable Intent
│   │   ├── PersonaTable.tsx      # Bảng editable Persona
│   │   └── PromptTable.tsx       # Bảng editable Test Prompt
│   ├── pages/            # Các trang chính
│   │   ├── InputPage.tsx         # Bước 0: Upload CSV / Paste text
│   │   ├── IntentPage.tsx        # Bước 1: Review Intent
│   │   ├── PersonaPage.tsx       # Bước 2: Review Persona
│   │   └── PromptPage.tsx        # Bước 3: Review Test Prompt + Export
│   ├── App.tsx
│   └── main.tsx
├── package.json
└── README.md
```

## Backend API Endpoints

Backend chạy tại `http://localhost:8000`. Chi tiết API docs: `http://localhost:8000/docs`

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
