# Tech Spec — Ingestion đa nguồn + Lọc nhiễu để tối ưu Detect Intent

**Vai trò tài liệu:** Đây là **bản Tech Spec — *how*** (nguồn sự thật cho engineer khi code). Phần *why / what* (Problem, User Stories, Scope, Success Metrics, Fallback UX) nằm ở **[PRD_Ingestion.md](PRD_Ingestion.md)**.
**Phạm vi commit:** Phase 1 (A + B). Phase 2 (C) ghi để giữ north-star.

## 1. Kiến trúc & luồng dữ liệu
```
[Apify cào social]  →  file JSON/CSV ─┐
[survey files xlsx/csv/json/md/txt]  ─┤
[text dán tay: post+comment]         ─┼─→ A: Loader (factory chọn theo nguồn/đuôi file)
                                       │      → RawInput (common format)
[PRD file]  ──────────────────────────┘      → B: Normalize + lọc + dedup
                                              → merge_sources (gộp; PRD tách làm guidance)
                                              → IntentAgent (chunk → LLM → parse → dedup)
                                              → intents
```
**Tái dùng:** `DataIngestion` ABC ([base.py](backend/src/ingestion/base.py)) `load() -> RawInput`, mirror [csv_loader.py](backend/src/ingestion/csv_loader.py); cơ chế `guidance`+`memory_context` của IntentAgent ([intent_extractor.py:123-133](backend/src/pipeline/intent_extractor.py#L123-L133)) cho PRD-guidance — **không sửa SYSTEM_PROMPT**.

## 2. Common format
Dùng `RawInput` sẵn có ([schemas.py:108](backend/src/models/schemas.py#L108)), **không đổi schema gốc**:
- `content: str` — **bắt buộc**, text đã normalize, ghép từ mọi nguồn → cái LLM ăn vào.
- `source_type: str` ∈ {social, survey, prd, text}.
- `metadata: dict` — **bản structured optional** mỗi record (platform, author, timestamp, post_id, filename...) cho phase C. Nguồn thiếu (copy-paste) → để rỗng, hệ thống vẫn chạy.

**Nguyên tắc:** `content` là mẫu số chung tối thiểu; field cấu trúc là bonus, luôn optional.

## 3. Functional Requirements (Phase 1)

### A — Ingestion loaders (mirror [csv_loader.py](backend/src/ingestion/csv_loader.py))
- **FR-A1** `ExcelLoader` (xlsx, pandas + openpyxl) — gộp cột text như CSVLoader.
- **FR-A2** `JsonLoader` (json/jsonl) — flatten field text theo whitelist key: `text, content, comment, message, body, caption, title` (case-insensitive); nested → duyệt đệ quy.
- **FR-A3** `MarkdownLoader` (md/txt) — md strip cú pháp nhẹ; txt tái dùng `TextLoader`.
- **FR-A4** `SocialLoader` đọc export Apify (JSON/CSV) → list utterance + provenance vào metadata (xem §6 mapping).
- **FR-A5** `loader_factory.get_loader(source_type|filename)` chọn loader theo đuôi/loại nguồn.
- **FR-A6** Text dán tay vẫn qua `TextLoader` (case tối giản, đã có).

### B — Normalize / lọc nhiễu / PRD-guidance
- **FR-B1** `normalizer` (tham số cụ thể ở §7).
- **FR-B2** `merge_sources(list[RawInput]) -> RawInput`: gộp vào 1 `content` với separator có nhãn nguồn (`\n---[social:tiktok]---\n`).
- **FR-B3** `PRDLoader`: trích text PRD (md/txt) → **guidance string** (xử lý PRD dài ở §8), KHÔNG vào content; lưu `state.raw_prd_guidance` (thêm field vào `PipelineState` [schemas.py:116](backend/src/models/schemas.py#L116)).
- **FR-B4** Hook `dedup_semantic()` (no-op phase 1) thay chỗ `_deduplicate` lowercase yếu ([intent_extractor.py:167](backend/src/pipeline/intent_extractor.py#L167)) — để phase C cắm vào.

### API & Frontend
- **FR-API1/2, FR-FE1/2** — xem §5 (API Contract) và §9 (Frontend).

## 4. Non-functional Requirements
- **NFR1 Pluggability (adapter):** logic riêng-tool chỉ trong loader; pipeline/normalizer/IntentAgent **cấm** nhánh "nếu là Apify…". Đổi tool = 1 loader mới.
- **NFR2 Graceful degradation:** field cấu trúc optional; nguồn thiếu metadata vẫn chạy bằng `content`.
- **NFR3 Tương thích ngược:** luồng paste-text qua `/api/discover` không hỏng.
- **NFR4 Cost/Privacy:** Apify có phí + data qua bên thứ 3 → không hardcode token (đọc từ env/config).
- **NFR5 Ngôn ngữ:** ưu tiên tiếng Việt — không "chuẩn hóa" làm mất văn phong chat.

## 5. API Contract — `POST /api/ingest` *(gap #1)*
**Request** (`multipart/form-data`):
| Field | Kiểu | Mô tả |
|---|---|---|
| `files[]` | file (n) | Các file nạp (xlsx/csv/json/md/txt). |
| `types[]` | string (n) | `source_type` song song theo index với `files[]` ∈ {social, survey, prd}. Nếu thiếu → suy ra từ đuôi file (default `survey`). |
| `prd_file` | file (optional) | File PRD riêng (nếu không gắn qua `types[]=prd`). |

> Quy ước: `files[i]` ↔ `types[i]`. File `type=prd` → đi `PRDLoader` (vào guidance), KHÔNG vào content.

**Response** `200`:
```json
{
  "sources": [
    {"source_type":"social","filename":"tiktok.json","rows_in":1200,"rows_after_dedup":840,"status":"ok"},
    {"source_type":"survey","filename":"survey2.xlsx","rows_in":0,"rows_after_dedup":0,"status":"skipped"}
  ],
  "prd_loaded": true,
  "total_chars": 53000,
  "warnings": ["survey2.xlsx: 0 dòng text hợp lệ → skip"]
}
```
**Side effect:** set `state.raw_input` (merged content) + `state.raw_prd_guidance`; **không** tự chạy discover.
**Errors:** 400 nếu không có file hợp lệ nào (tất cả skip). Lỗi 1 file → đưa vào `warnings`, không fail cả request (per-file graceful skip).

**FR-API2 — sửa `discover_intents`** ([frontend_api.py:225](backend/src/api/routers/frontend_api.py#L225)): nếu `logsText` rỗng → dùng `state.raw_input` đã ingest; nối `state.raw_prd_guidance` vào `ruleText`. Giữ tương thích ngược đường paste-text.

## 6. Apify export — sample & field mapping *(gap #2)*
> ⚠️ **CẦN VERIFY:** schema dưới là **giả định** từ Actor Apify phổ biến. Teammate phụ trách Apify cung cấp 1 file export thật để chốt; nếu khác, chỉ sửa map trong `SocialLoader` (NFR1).

**Sample (Apify TikTok/FB comment Actor — rút gọn):**
```json
[
  {"text":"sạc ở đâu vậy mn ơi", "authorMeta":{"name":"user123"},
   "createTimeISO":"2026-05-01T10:00:00Z", "postId":"7xxx", "diggCount":12}
]
```
**Mapping → RawInput:**
| Apify field | → đích | Ghi chú |
|---|---|---|
| `text` (hoặc `commentText`/`content`) | `content` (1 utterance) | **bắt buộc**; thiếu → bỏ record |
| `authorMeta.name` (hoặc `ownerUsername`) | `metadata.author` | optional |
| `createTimeISO` (hoặc `timestamp`) | `metadata.timestamp` | optional |
| `postId` (hoặc `videoUrl`) | `metadata.post_id` | optional |
| — | `source_type` = `social`, `metadata.platform` = tiktok/fb/threads | set bởi loader |

## 7. Normalizer — tham số cụ thể *(gap #3)*
Thứ tự xử lý trong `normalizer.normalize(lines)`:
1. **Strip** khoảng trắng, ký tự điều khiển, HTML tag (nếu có).
2. **Bỏ dòng quá ngắn:** < 3 từ HOẶC < 10 ký tự → loại (giữ utterance ngắn kiểu " k đc" thì dùng ngưỡng từ, cân nhắc 2 từ — *để mặc định 3 từ, chỉnh được qua param*).
3. **Dedup exact:** so khớp sau khi `.strip().lower()` (case-insensitive) → giữ bản đầu.
4. **Lọc ngôn ngữ (optional, default off):** `langdetect`, giữ `vi`; confidence < 0.7 thì **giữ lại** (tránh loại nhầm câu chêm tiếng Anh) — NFR5.
- Hàm `merge_sources` chạy **sau** normalize từng nguồn.
- Tham số (`min_words=3`, `lang_filter=False`, `keep_lang="vi"`) đặt trong signature để dễ test & chỉnh.

## 8. Rủi ro kỹ thuật cần xử lý
- **PRD dài → guidance** *(gap #4):* `PRDLoader` truncate guidance ở ngưỡng (vd 4000 ký tự); nếu PRD dài hơn → cắt + ghi chú, hoặc (tùy chọn) summarize bằng 1 LLM call. **Không** nhồi nguyên PRD vào guidance → tránh vỡ context.
- **Merge × chunking** *(gap #5):* tổng `content` sau merge vẫn đi qua `chunk_text` (50k token). Nếu vượt nhiều chunk → giữ nguyên cơ chế hiện tại; ưu tiên thứ tự nguồn social → survey khi cần cắt (cấu hình ở merge).

## 9. Frontend *(FR-FE1/2 + wireframe — gap #7)*
- Upload **nhiều file** + chọn `source_type` mỗi file; ô upload PRD riêng; ô dán text social vẫn còn.
- Chuyển sang **`FormData` server-side** (bắt buộc cho xlsx/binary) → gọi `/api/ingest` rồi `/api/discover`. Tách `handleDiscover` ([App.tsx:116](frontend/src/App.tsx#L116)) thành `handleIngest` + `handleDiscover`.

**Wireframe (ASCII):**
```
┌─ Data Ingestion ─────────────────────────────────┐
│ [ + Add files ]   (xlsx/csv/json/md/txt)         │
│ ┌───────────────────────────────────────────┐    │
│ │ tiktok.json     [source: social ▼]   (x)  │    │
│ │ survey_q2.xlsx  [source: survey ▼]   (x)  │    │
│ └───────────────────────────────────────────┘    │
│ PRD context:  [ Upload PRD ]  prd.md (loaded)     │
│ Or paste raw text: [ ........................ ]   │
│ ─────────────────────────────────────────────    │
│ Ingest preview:  social 1200→840 · survey 0 skip  │
│                  [ Run Intent Discovery ]         │
└──────────────────────────────────────────────────┘
```

## 10. Files tạo/sửa
- **Tạo** (`backend/src/ingestion/`): `excel_loader.py`, `json_loader.py`, `markdown_loader.py`, `social_loader.py`, `prd_loader.py`, `loader_factory.py`, `normalizer.py`.
- **Sửa**: [frontend_api.py](backend/src/api/routers/frontend_api.py) (`/api/ingest`, sửa `discover_intents`), [schemas.py](backend/src/models/schemas.py) (`raw_prd_guidance`), [intent_extractor.py](backend/src/pipeline/intent_extractor.py) (hook `dedup_semantic`), [DataIngestionTab.tsx](frontend/src/components/DataIngestionTab.tsx) + [App.tsx](frontend/src/App.tsx).
- **Dependency**: thêm `openpyxl` (+ `langdetect` nếu bật lọc ngôn ngữ).

## 11. Build sequencing / milestones *(gap #6)*
| # | Milestone | Phụ thuộc | Output kiểm được |
|---|---|---|---|
| 1 | `loader_factory` + Excel/Json/Markdown loaders + fixtures | — | Unit test pass cho 3 định dạng |
| 2 | `SocialLoader` + `PRDLoader` | M1, sample Apify (§6) | Loader social/PRD ra RawInput/guidance đúng |
| 3 | `normalizer` + `merge_sources` + hook `dedup_semantic` no-op | M1 | Dedup + merge có nhãn nguồn |
| 4 | `schemas.raw_prd_guidance` + `POST /api/ingest` + sửa `discover_intents` | M1–M3 | API contract §5 trả đúng stats |
| 5 | Frontend multi-file + FormData + preview stats | M4 | E2E upload đa nguồn |
| 6 | E2E + regression paste-text | M5 | Acceptance §12 |

## 12. Acceptance Criteria / Verification
1. **Unit:** mỗi loader đọc fixture → `RawInput.content` đúng, metadata có provenance; `normalizer` (dedup + merge + min_words); `PRDLoader` trả guidance (mirror [tests/test_schemas.py](backend/tests/test_schemas.py)).
2. **API:** `POST /api/ingest` (1 xlsx survey + 1 social json Apify + 1 PRD md) → response stats đúng schema §5; `state.raw_input` gộp đúng; `state.raw_prd_guidance` có nội dung; file 0-dòng → `status:"skipped"` + warning.
3. **E2E:** backend ([main.py](backend/main.py)) + frontend → upload đa nguồn → "Run Intent Discovery" → intent phản ánh cả social lẫn survey; PRD ảnh hưởng định hướng, không tạo intent từ PRD.
4. **Edge:** dán 1 đoạn post+comment ngẫu nhiên → ra intent qua TextLoader; 1 file corrupt → skip + warn.
5. **Regression:** luồng paste-text cũ vẫn chạy.

**Fixtures cần tạo** *(gap #8):* `sample_survey.xlsx`, `sample_apify_tiktok.json`, `sample_prd.md`, `sample_corrupt.json` (trong `backend/tests/fixtures/`).

## 13. Open Questions (đã khóa default, override được)
- **Common format**: default = `content` text + structured trong `metadata`. Override → JSONL structured thuần (phải sửa IntentAgent đọc structured).
- **Apify P1**: default = export thủ công rồi upload. Override → tích hợp API ngay (kéo C lên sớm).
- **Định dạng file**: default = chỉ text-based (md/txt/csv/json/xlsx). Override → +DOCX (python-docx) / +PDF (pypdf).
- **Schema social Apify cụ thể**: §6 đang giả định — **cần teammate Apify cung cấp 1 export thật để verify** trước M2.

## 14. Phase 2 (ngoài phạm vi, north-star)
- C: embedding (BGE/multilingual) + clustering cho riêng luồng social, cắm vào `dedup_semantic()`; LLM-in-the-loop chấm cụm Good/Bad (Dial-In LLM, arXiv 2412.09049) thay dedup lowercase.
- Tích hợp Apify API (live-crawl tự động) thay export thủ công.
