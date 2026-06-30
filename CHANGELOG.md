# Changelog

## [Chưa phát hành] — 2026-06-30 (nhánh `feat/intent-merge-cite`) — UI tweaks

Dọn dẹp UI các tab ingest / persona / test-case và popup chờ.

### Added — Tính năng mới
- **Xuất file Persona**: thêm nút **Export JSON** / **Export CSV** ở tab Persona (cạnh dropdown chọn intent). CSV kèm cả tên intent đã resolve.
  `frontend/src/components/PersonaPlaygroundTab.tsx`, `frontend/src/utils/exportPersonas.ts`

### Changed — Thay đổi
- **Data Ingestion**: ẩn ô nhập "posts mỗi keyword", **cố định = 1** (không cho người dùng chỉnh).
  `frontend/src/components/DataIngestionTab.tsx`
- **Popup chờ (OperationConsole)**: bỏ bộ đếm `step x / N` ở góc header.
  `frontend/src/components/OperationConsole.tsx`

### Removed — Gỡ bỏ
- **Nút "Include viral signals"** (Data Ingestion): gỡ hẳn vì cờ `isViral` không bao giờ được gửi xuống backend → chỉ là UI giả.
  `frontend/src/components/DataIngestionTab.tsx`
- **Banner "Configure Generation Rules"** ở tab Test case (Export): gỡ banner + prop `onOpenRuleModal` không còn dùng.
  `frontend/src/components/ExportTab.tsx`, `frontend/src/App.tsx`
- **Xóa `DataIngestionTab_ver2.tsx`**: file không được import ở đâu (dead code, dùng `onDiscoverSocial` mock thay vì `onCrawlSocial` thật).

## [Chưa phát hành] — 2026-06-30 (nhánh `vietanh`)

Tập trung vào màn **Intent Curation**: cột trích dẫn (CITE), gộp intent PRD↔DATA, gap-analysis đa-provider, và sửa lỗi trích nguồn từ crawl data.

### Added — Tính năng mới
- **Cột CITE** (đổi tên từ "Post"): hiển thị trích dẫn nguồn của intent — gồm **trích dẫn PRD nguyên văn** và **bài social (source posts)**.
  `frontend/src/components/IntentCurationTab.tsx`
- **Gộp intent PRD + DATA đã match thành 1 dòng** (`confirmed`):
  - Backend gộp theo **connected-components** trên `matchedIds` (`_build_merged_intents`); cụm có cả PRD lẫn DATA → 1 intent, lấy name/utterance/trigger từ **data nhiều source post nhất**.
  - Intent gộp mang **nhiều nhãn nguồn** (`sources`, vd `["prd","data"]`) và **nhiều trích dẫn PRD** (`prdSources`), cite cắt ≤3 PRD quote + ≤3 post.
  - FE chỉ render (Source hiện nhiều badge, CITE đọc thẳng `prdSources`/`sourcePosts`).
  `backend/src/api/routers/frontend_api.py`, `backend/src/models/schemas.py`, `frontend/src/components/IntentCurationTab.tsx`, `frontend/src/types.ts`
- **Embedding cho gap-analysis hỗ trợ OpenAI** (trước đây chỉ Gemini): `IntentComparator` chọn provider theo LLM đang dùng (gemini: `models/gemini-embedding-001`, openai: `text-embedding-3-small`).
  `backend/src/pipeline/intent_comparator.py`, `backend/src/config.py` (thêm `openai_embedding_model`)
- **Export**: CSV thêm cột `prd_sources`; cột `source` xuất theo danh sách `sources` (nối bằng `|`). JSON tự kèm field mới.
  `frontend/src/utils/exportIntents.ts`
- **Sơ đồ luồng xử lý** data/prd → intent (Mermaid).
  `Data Source Intent Merge-2026-06-30-060159.mmd`

### Fixed — Sửa lỗi
- **PRD Source hiển thị nhầm text social**: `prdSource` chỉ lấy `raw_observation` khi `source == "prd"` (data/prd_inferred không nhồi nhầm).
  `backend/src/api/routers/frontend_api.py`
- **Mất trích nguồn từ crawl data** (sau khi đổi LLM sang OpenAI): `_attribute_source_posts` đổi từ **so khớp chuỗi con chính xác** sang **so khớp fuzzy theo độ trùng token** (containment ≥ 0.45, cộng điểm khi trùng nguyên văn) → chịu được paraphrase. Nhờ đó intent `confirmed` hiện đủ cả nguồn PRD + DATA.
  `backend/src/api/routers/frontend_api.py`
- **Mất cột Coverage**: nguyên nhân là embedding gap-analysis nhận sai key (LLM=OpenAI nhưng embedding gọi Gemini) → comparator degrade, xoá `coverage`/`matchedIds`. Đã khắc phục bằng đường embedding OpenAI ở trên.
  `backend/src/api/routers/frontend_api.py`, `backend/src/pipeline/intent_comparator.py`

### Changed — Thay đổi
- `state.internal_intents` được dựng **mirror theo intent đã gộp** (1:1 theo id) → persona/test-case sinh 1 bộ cho mỗi intent gộp, hết trùng.
  `backend/src/api/routers/frontend_api.py`
- 2 pool gốc `state.prd_intents` / `state.data_intents` **giữ nguyên** (phục vụ re-discover theo scope + cache PRD); việc gộp chỉ là phép chiếu tạo `state.intents`.
  `backend/src/api/routers/frontend_api.py`

### Notes — Ghi chú
- Gap-analysis (coverage) cần **một provider còn quota** (OpenAI có credit hoặc Gemini key hợp lệ); nếu embedding lỗi, hệ thống degrade (bỏ coverage) chứ không crash.
- Ngưỡng fuzzy `THRESHOLD = 0.45` có thể tinh chỉnh: giảm để bắt cite rộng hơn, tăng nếu dính cite sai.
