# Tech Spec — Ingestion đa nguồn + Lọc nhiễu để tối ưu Detect Intent

**Vai trò tài liệu:** Đây là **bản Tech Spec — *how*** (nguồn sự thật cho engineer khi code). Phần *why / what* (Problem, User Stories, Scope, Success Metrics, Fallback UX) nằm ở **[PRD_Ingestion.md](PRD_Ingestion.md)**.
**Phạm vi commit:** Phase 1 (A + B). Phase 2 (C) ghi để giữ north-star.

## 1. Kiến trúc & luồng dữ liệu
```
[Apify cào social]  →  file JSON/CSV ─┐
[survey files xlsx/csv/json/md/txt]  ─┤→ A: Loader (factory) → RawInput
[text dán tay: post+comment]         ─┘   → B: Normalize + lọc + dedup
                                          → merge_sources (gộp data thật; nhãn nguồn)
                                          → IntentAgent (chunk → LLM → parse) → data_intents (source=data)
                                                                                          │
[PRD file] → PRDLoader ─┬→ guidance ──(nối vào ruleText khi mine data)──────────────────┤
                        └→ content  → IntentAgent → prd_intents (source=prd) ────────────┤
                                                                                          ▼
                                          IntentComparator (hybrid: embedding lọc → vùng xám LLM chấm)
                                          → mỗi intent gắn coverage ∈ {confirmed, prd_only, data_only}
                                          → intents (FEIntent có source + coverage)
```
**Tái dùng:** `DataIngestion` ABC ([base.py](backend/src/ingestion/base.py)) `load() -> RawInput`, mirror [csv_loader.py](backend/src/ingestion/csv_loader.py); cơ chế `guidance`+`memory_context` của IntentAgent ([intent_extractor.py:123-133](backend/src/pipeline/intent_extractor.py#L123-L133)) cho PRD-guidance — **không sửa SYSTEM_PROMPT**; field `source` sẵn có trên `Intent` ([schemas.py:58](backend/src/models/schemas.py#L58)).

> **Thay đổi quan trọng so với draft đầu:** PRD đi **2 nhánh** (content để mine + guidance để định hướng). Sau khi có 2 tập intent, thêm khối **IntentComparator** đối chiếu — đây là phần thay/đổi mục đích của hook `dedup_semantic` (FR-B4): từ "xoá trùng" → "ghép cặp + phân loại đủ/thiếu". Tuyệt đối **không gộp PRD vào chung `merge_sources`** với data thật, vì cần giữ 2 tập tách biệt để đối chiếu.

## 2. Common format
Dùng `RawInput` sẵn có ([schemas.py:108](backend/src/models/schemas.py#L108)), **không đổi schema gốc**:
- `content: str` — **bắt buộc**, text đã normalize, ghép từ mọi nguồn → cái LLM ăn vào.
- `source_type: str` ∈ {social, survey, prd, text}. Với `prd`: content được **mine ra intent** (PRD-as-source), đồng thời tách phần guidance riêng (xem FR-B3).
- `metadata: dict` — **bản structured optional** mỗi record (platform, author, timestamp, post_id, filename...) cho phase C. Nguồn thiếu (copy-paste) → để rỗng, hệ thống vẫn chạy.

**Nguyên tắc:** `content` là mẫu số chung tối thiểu; field cấu trúc là bonus, luôn optional.

**Field mới trên intent (để gap analysis):**
- Trên `Intent` ([schemas.py:52](backend/src/models/schemas.py#L52)) tái dùng `source` (đã có) = `"data" | "prd"`.
- Trên **`FEIntent`** ([schemas.py:14](backend/src/models/schemas.py#L14)) thêm: `source: str = "data"`, `coverage: str = ""` (∈ `confirmed | prd_only | data_only`), optional `matchedIds: list[str]`. `frontend/src/types.ts` cập nhật tương ứng.
- Thêm `PipelineState.raw_prd_content` + `raw_prd_guidance` ([schemas.py:116](backend/src/models/schemas.py#L116)).

## 3. Functional Requirements (Phase 1)

### A — Ingestion loaders (mirror [csv_loader.py](backend/src/ingestion/csv_loader.py))
- **FR-A1** `ExcelLoader` (xlsx, pandas + openpyxl) — gộp cột text như CSVLoader.
- **FR-A2** `JsonLoader` (json/jsonl) — flatten field text theo whitelist key: `text, content, comment, message, body, caption, title` (case-insensitive); nested → duyệt đệ quy.
- **FR-A3** `MarkdownLoader` (md/txt) — md strip cú pháp nhẹ; txt tái dùng `TextLoader`.
- **FR-A4** `SocialLoader` đọc export Apify (JSON/CSV) → list utterance + provenance vào metadata (xem §6 mapping).
- **FR-A5** `loader_factory.get_loader(source_type|filename)` chọn loader theo đuôi/loại nguồn.
- **FR-A6** Text dán tay vẫn qua `TextLoader` (case tối giản, đã có).

### B — Normalize / lọc nhiễu / PRD-as-source / Gap Analysis
- **FR-B1** `normalizer` (tham số cụ thể ở §7).
- **FR-B2** `merge_sources(list[RawInput]) -> RawInput`: gộp **chỉ data thật** (social/survey/text) vào 1 `content` với separator có nhãn nguồn (`\n---[social:tiktok]---\n`). **PRD KHÔNG nằm trong merge này.**
- **FR-B3** `PRDLoader`: trích text PRD (md/txt) → trả **CẢ HAI**: (a) `content` để mine intent (tái dùng `MarkdownLoader`) → lưu `state.raw_prd_content`; (b) `guidance string` (truncate ~4000 ký tự, §8) → lưu `state.raw_prd_guidance`, nối vào `ruleText` khi mine data thật. *(Khác draft cũ: trước đây PRD chỉ ra guidance, không vào content.)*
- **FR-B4** Hook `dedup_semantic()` — **đổi mục đích**: không còn là no-op "xoá trùng" mà trở thành điểm tích hợp logic so khớp ngữ nghĩa (FR-B5). `_deduplicate` lowercase cũ ([intent_extractor.py:167](backend/src/pipeline/intent_extractor.py#L167)) vẫn giữ cho dedup **trong cùng 1 nguồn**; KHÔNG dùng để gộp chéo PRD↔data (sẽ che mất tín hiệu Confirmed).
- **FR-B5 (mới) `IntentComparator`** (`backend/src/pipeline/intent_comparator.py`): nhận `prd_intents` + `data_intents`, đối chiếu **hybrid**:
  1. Embed mỗi intent từ `intent_name + " " + utterance + " " + moment`.
  2. Cosine similarity matrix `prd × data`.
  3. `sim ≥ HIGH` (default 0.85) → auto match; `sim ≤ LOW` (default 0.55) → auto khác; `LOW < sim < HIGH` → **vùng xám** → 1 LLM-pass chấm "cùng intent? yes/no" (gom batch tiết kiệm call).
  4. Suy ra `coverage`: PRD intent có ≥1 match → `confirmed` (cả 2 bên); PRD intent không match → `prd_only`; data intent không match PRD nào → `data_only`.
  - Ngưỡng HIGH/LOW **cấu hình được** (settings). Standalone (chỉ 1 phía) → bỏ qua đối chiếu, intent giữ `source` gốc, `coverage=""`.

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

**FR-API2 — sửa `discover_intents`** ([frontend_api.py:225](backend/src/api/routers/frontend_api.py#L225)):
- Nếu `logsText` rỗng → dùng `state.raw_input` đã ingest; nối `state.raw_prd_guidance` vào `ruleText`.
- Mine data → `data_intents` (gắn `source=data`); nếu có `state.raw_prd_content` → mine song song → `prd_intents` (gắn `source=prd`).
- Gọi `IntentComparator(prd_intents, data_intents)` → mỗi intent có `source` + `coverage` (+ `matchedIds`).
- Map qua `_map_pipeline_intents_to_fe` (**mở rộng** map thêm `source`, `coverage`, `matchedIds`); trả về list FEIntent đã gắn nhãn.
- **Standalone:** chỉ data → như cũ (`coverage=""`); chỉ PRD → tất cả `source=prd`, không đối chiếu.
- Giữ tương thích ngược đường paste-text (không PRD, không ingest → hành vi cũ).

**Response `discover` (bổ sung field):** mỗi phần tử `intents[]` thêm `source` và `coverage`, ví dụ:
```json
{"intents":[
  {"id":"a1","name":"Đặt lịch lái thử","source":"prd","coverage":"confirmed","matchedIds":["b7"]},
  {"id":"b7","name":"đặt lái thử vf8 t7","source":"data","coverage":"confirmed","matchedIds":["a1"]},
  {"id":"c3","name":"Báo trạm sạc hỏng","source":"data","coverage":"data_only","matchedIds":[]}
], "fallback": false}
```

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
- **Ngưỡng embedding HIGH/LOW** *(mới):* phải hiệu chỉnh thực nghiệm theo data tiếng Việt (gold set ~30 cặp, xem RA2 ở PRD). Cấu hình trong settings, không hardcode. Mặc định khởi điểm 0.85 / 0.55.
- **Mine PRD bằng SYSTEM_PROMPT hiện tại** *(mới):* prompt đòi "câu chat thật VN" trong khi PRD là văn bản formal → `utterance` của intent bóc từ PRD sẽ mang tính **suy diễn**. Chấp nhận ở Phase 1 (không sửa SYSTEM_PROMPT). Nếu kém → nhánh prompt riêng cho `source=prd` ở vòng sau.
- **Chi phí matching** *(mới):* embedding O(n_prd × n_data) cặp, nhưng chỉ vùng xám mới gọi LLM → gom batch cặp xám trong 1-vài prompt để kiểm soát số call.

## 9. Frontend *(FR-FE1/2 + wireframe — gap #7)*
- Upload **nhiều file** + chọn `source_type` mỗi file; ô upload PRD riêng; ô dán text social vẫn còn.
- Chuyển sang **`FormData` server-side** (bắt buộc cho xlsx/binary) → gọi `/api/ingest` rồi `/api/discover`. Tách `handleDiscover` ([App.tsx:116](frontend/src/App.tsx#L116)) thành `handleIngest` + `handleDiscover`.
- **Bảng curation** ([IntentCurationTab.tsx](frontend/src/components/IntentCurationTab.tsx)) thêm **cột Source** (PRD/Data) + **badge Coverage** (Confirmed / PRD-only / Data-only, màu khác nhau) + **filter** theo coverage để researcher thấy ngay chỗ thiếu (Data-only) và chỗ thừa (PRD-only). Cập nhật `Intent` type ([frontend/src/types.ts](frontend/src/types.ts)).

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
**Bảng curation (sau discover) — thêm cột đối chiếu:**
```
┌─ Intent Curation ────────────────────────────────────────────────┐
│ Filter coverage: [ All ▼ ]  (All / Confirmed / PRD-only / Data-only)│
│ ┌──────────────────────────┬────────┬───────────┐                 │
│ │ Intent name              │ Source │ Coverage  │                 │
│ ├──────────────────────────┼────────┼───────────┤                 │
│ │ Đặt lịch lái thử VF8     │ PRD    │ ✅Confirmed│                 │
│ │ Báo trạm sạc hỏng        │ Data   │ ⚠️Data-only│ ← chỗ THIẾU     │
│ │ Xuất hoá đơn điện tử     │ PRD    │ ◻️PRD-only │ ← nghi THỪA     │
│ └──────────────────────────┴────────┴───────────┘                 │
└───────────────────────────────────────────────────────────────────┘
```

## 10. Files tạo/sửa
- **Tạo** (`backend/src/ingestion/`): `excel_loader.py`, `json_loader.py`, `markdown_loader.py`, `social_loader.py`, `prd_loader.py`, `loader_factory.py`, `normalizer.py`.
- **Tạo** (`backend/src/pipeline/`): **`intent_comparator.py`** (FR-B5, hybrid embedding + LLM) + helper `embed()`.
- **Sửa**: [frontend_api.py](backend/src/api/routers/frontend_api.py) (`/api/ingest`, sửa `discover_intents` + comparator), [schemas.py](backend/src/models/schemas.py) (`raw_prd_content` + `raw_prd_guidance`; `FEIntent.source/coverage/matchedIds`), [intent_extractor.py](backend/src/pipeline/intent_extractor.py) (hook `dedup_semantic` đổi mục đích), [DataIngestionTab.tsx](frontend/src/components/DataIngestionTab.tsx) + [App.tsx](frontend/src/App.tsx) + [IntentCurationTab.tsx](frontend/src/components/IntentCurationTab.tsx) (cột Source/Coverage) + [types.ts](frontend/src/types.ts).
- **Dependency**: thêm `openpyxl`; **embedding SDK** theo provider (OpenAI/Gemini embedding API — ưu tiên, tránh model local) (+ `langdetect` nếu bật lọc ngôn ngữ).

## 11. Build sequencing / milestones *(gap #6)*
| # | Milestone | Phụ thuộc | Output kiểm được |
|---|---|---|---|
| 1 | `loader_factory` + Excel/Json/Markdown loaders + fixtures | — | Unit test pass cho 3 định dạng |
| 2 | `SocialLoader` + `PRDLoader` (content + guidance) | M1, sample Apify (§6) | Loader social ra RawInput; PRD ra cả content lẫn guidance |
| 3 | `normalizer` + `merge_sources` (data thật) | M1 | Dedup + merge có nhãn nguồn |
| 4 | **`IntentComparator`** (embedding + LLM gray-zone) + đổi `dedup_semantic` | M2 | Gold set → phân đúng confirmed/prd_only/data_only |
| 5 | `schemas` (raw_prd_content + FEIntent fields) + `POST /api/ingest` + sửa `discover_intents` | M1–M4 | API contract §5 trả stats; discover trả `source`+`coverage` |
| 6 | Frontend multi-file + FormData + preview stats + cột Source/Coverage | M5 | E2E upload đa nguồn + PRD |
| 7 | E2E + regression paste-text | M6 | Acceptance §12 |

## 12. Acceptance Criteria / Verification
1. **Unit:** mỗi loader đọc fixture → `RawInput.content` đúng, metadata có provenance; `normalizer` (dedup + merge + min_words); `PRDLoader` trả **cả content lẫn guidance**; **`IntentComparator`** với cặp giả lập (mock LLM) → phân đúng confirmed/prd_only/data_only và vùng xám gọi LLM (mirror [tests/test_schemas.py](backend/tests/test_schemas.py)).
2. **API:** `POST /api/ingest` (1 xlsx survey + 1 social json Apify + 1 PRD md) → response stats đúng schema §5; `state.raw_input` gộp đúng; `state.raw_prd_content` + `state.raw_prd_guidance` có nội dung; file 0-dòng → `status:"skipped"` + warning.
3. **E2E (gap analysis):** backend ([main.py](backend/main.py)) + frontend → upload PRD + nguồn ngoài → "Run Intent Discovery" → bảng curation hiện **cột Source + Coverage**; **Data-only** lộ chỗ thiếu, **PRD-only** lộ chỗ thừa, **Confirmed** ở cả 2 bên. PRD ảnh hưởng định hướng (guidance) **đồng thời** được bóc thành intent (source=prd).
4. **Standalone PRD:** chỉ upload PRD (không nguồn ngoài) → vẫn ra intent từ PRD (`source=prd`, `coverage=""`).
5. **Edge:** dán 1 đoạn post+comment ngẫu nhiên → ra intent qua TextLoader; 1 file corrupt → skip + warn.
6. **Regression:** luồng paste-text cũ qua `/api/discover` (không PRD, không ingest) vẫn chạy ra intent bình thường.

**Fixtures cần tạo** *(gap #8):* `sample_survey.xlsx`, `sample_apify_tiktok.json`, `sample_prd.md`, `sample_corrupt.json` (trong `backend/tests/fixtures/`); **gold set ~30 cặp PRD↔data** để hiệu chỉnh ngưỡng matching.

## 13. Open Questions (đã khóa default, override được)
- **Common format**: default = `content` text + structured trong `metadata`. Override → JSONL structured thuần (phải sửa IntentAgent đọc structured).
- **Apify P1**: default = export thủ công rồi upload. Override → tích hợp API ngay (kéo C lên sớm).
- **Định dạng file**: default = chỉ text-based (md/txt/csv/json/xlsx). Override → +DOCX (python-docx) / +PDF (pypdf).
- **Schema social Apify cụ thể**: §6 đang giả định — **cần teammate Apify cung cấp 1 export thật để verify** trước M2.
- **Embedding model (mới)**: default = embedding API của provider sẵn có (OpenAI `text-embedding-3-small` / Gemini `text-embedding-004`) để tránh model local nặng. Override → local multilingual (BGE-m3 / multilingual-e5) nếu cần offline/chi phí.
- **Ngưỡng matching HIGH/LOW (mới)**: default 0.85 / 0.55, cấu hình trong settings; cần gold set để chốt số thực tế cho tiếng Việt.
- **Mine PRD với prompt nào (mới)**: default = dùng chung SYSTEM_PROMPT hiện tại (chấp nhận utterance suy diễn). Override → nhánh prompt riêng cho `source=prd`.

## 14. Phase 2 (ngoài phạm vi, north-star)
- C: embedding (BGE/multilingual) + clustering cho riêng luồng social volume lớn (mở rộng từ embedding matching của Phase 1); LLM-in-the-loop chấm cụm Good/Bad (Dial-In LLM, arXiv 2412.09049).
- Tích hợp Apify API (live-crawl tự động) thay export thủ công.
