# Changelog

## [Chưa phát hành] — 2026-06-30 (nhánh `feat/intent-merge-cite`) — Flag & chẩn đoán persona sinh lỗi

Khi vòng lặp generate→evaluate→refine không tạo nổi cặp persona đạt rubric cho một intent, trước đây intent đó **âm thầm mất persona** — không cờ, không thông báo. Nay intent lỗi được **đánh dấu, hiển thị bản tốt nhất từng sinh + panel chẩn đoán** để user tự sửa; đồng thời chặn bug làm rớt persona ở bước REFINE.

### Added — Tính năng mới
- **Theo dõi "bản tốt nhất" mỗi intent qua các vòng loop** (`best_attempts`): evaluator node trích `pair_score` (0–28) vốn đã có sẵn từ LLM rồi snapshot cặp persona điểm cao nhất từng thấy cho mỗi `intent_num`. Cuối graph, intent nào còn lỗi sẽ được ghép lại bản tốt nhất này thay vì bản cuối (có thể rỗng/kém hơn).
  `backend/src/pipeline/persona_graph.py`
- **`failure_summary` + API `personaIssues`**: graph phát ra danh sách intent lỗi (điểm, lý do, gợi ý sửa). Thêm `PersonaAgent.run_with_diagnostics()` trả `(personas, failure_summary)` — giữ nguyên `run()` cho các caller cũ. Endpoint `/api/generate-personas` map sang `personaIssues` (keyed theo FE intent id) + trường `warning`.
  `backend/src/pipeline/persona_generator.py`, `backend/src/api/routers/frontend_api.py`
- **Tab Persona — dropdown chọn intent thiết kế lại + cờ + panel chẩn đoán**: thay `<select>` gốc bằng combobox tùy biến theo theme (trắng / stone-200 / bo vuông). Intent lỗi hiện icon ⚠️ + nhãn "Needs review" trong cả nút lẫn danh sách. Chọn vào intent lỗi hiện panel amber: điểm (x/28), lý do, danh sách gợi ý sửa; vẫn render cặp persona tốt nhất bên dưới nếu có.
  `frontend/src/components/PersonaPlaygroundTab.tsx`, `frontend/src/types.ts` (thêm interface `PersonaIssue`), `frontend/src/App.tsx` (state `personaIssues`, toast `warning`)

### Fixed — Sửa lỗi
- **Sinh persona cho TẤT CẢ intent thay vì chỉ intent đã chọn** (chọn 3 intent nhưng sinh 12 persona cho 6 intent, rồi FE lọc hiện 6): endpoint ưu tiên `state.internal_intents` (toàn bộ intent đã discover) và bỏ qua danh sách intent đã chọn mà FE gửi lên. Nay **lọc `internal_intents` theo id FE gửi** → chọn N intent sinh đúng 2N persona, khớp checkbox, khỏi lãng phí token.
  `backend/src/api/routers/frontend_api.py`
- **REFINE làm rớt persona (intent về 0 persona)**: bước REFINE trước đây **xoá cặp cũ trước khi sinh lại**; nếu LLM trả JSON bị cắt/hỏng (`_parse → []`) thì không có gì thay thế → intent mất sạch persona (vi phạm rule "đúng 2 persona/intent"). Đổi sang **merge không phá hủy**: chỉ xoá cặp cũ khi cặp mới parse thành công, ngược lại giữ nguyên bản trước đó.
  `backend/src/pipeline/persona_graph.py`
- **Intent thiếu persona không bị bắt**: `_apply_best_attempts` giờ phát hiện lỗi **theo cấu trúc** — đếm số persona/intent ở kết quả cuối; intent nào < 2 persona (hoặc còn trong `pairs_to_regenerate`) đều bị flag, kể cả khi evaluator không hề "thấy" nó nên không bao giờ đưa vào `pairs_to_regenerate`.
  `backend/src/pipeline/persona_graph.py`
- **Fallback hiện nhầm persona**: tab Persona không còn rơi vào nhánh "hiện 2 persona đầu tiên" cho intent đang bị flag (tránh hiện cặp của intent khác dưới panel chẩn đoán "0/28").
  `frontend/src/components/PersonaPlaygroundTab.tsx`

### Changed — Thay đổi
- **Prompt sinh persona ép tiếng Việt**: thêm mục `# LANGUAGE (mandatory)` + dịch toàn bộ ví dụ R0–R4 sang tiếng Việt, để output (`trigger`/`utterance`/`pain`/`reject`/...) luôn là tiếng Việt tự nhiên — `utterance` như người thật gõ (viết tắt, không dấu); key JSON giữ tiếng Anh.
  `backend/src/prompts/persona_generator_system.txt`
- **Chỉ dẫn / cảnh báo / thông báo không pass hiển thị bằng tiếng Việt**: ép evaluator xuất `fixes` và `persona_issues` bằng tiếng Việt (thêm `# LANGUAGE (mandatory)` + dịch ví dụ few-shot; giữ code tiêu chí P1–P5/R0/G1–G4, verdict, JSON key bằng tiếng Anh). Dịch nốt toast `warning` của endpoint và thông báo mặc định "chưa sinh được persona" sang tiếng Việt có dấu.
  `backend/src/prompts/persona_evaluator_system.txt`, `backend/src/api/routers/frontend_api.py`, `backend/src/pipeline/persona_graph.py`

### Notes — Ghi chú
- Nguyên nhân nền khiến JSON dễ bị cắt là `max_tokens=4096` (`anthropic_client.py`, `openrouter_client.py`); hai fix trên giúp **không mất dữ liệu** khi điều này xảy ra. Cân nhắc nâng `max_tokens` (vd 8192) để LLM sinh đủ ngay từ đầu — chưa thực hiện vì ảnh hưởng chi phí/độ trễ.

## [Chưa phát hành] — 2026-06-30 (nhánh `feat/intent-merge-cite`) — Reset workspace + UI polish

### Added — Tính năng mới
- **Modal xác nhận Reset Workspace** thay cho `confirm()` của trình duyệt. Reset nay **xoá cả crawl sheet** (`/api/crawl/posts/reset`) song song với `/api/state/reset`, và bắn `crawlResetSignal` để `DataIngestionTab` drop bản crawl đang giữ cục bộ (View Results trống, không còn feed Intent Discovery). Reset cũng clear `personaIssues` và `prdLoaded`.
  `frontend/src/App.tsx`, `frontend/src/components/DataIngestionTab.tsx`

### Changed — Thay đổi
- **Chống spam click nút "Process Selected"** (Intent Curation): nút bị **grey out + hiện spinner "Processing..."** trong lúc sinh persona (`processing = activeOp === "personas"`), tránh người dùng bấm liên tục tạo nhiều request. Các nút chạy lâu khác (Run Intent Discovery, Crawl, Confirm Personas, Regenerate) vốn đã tự disable khi chạy.
  `frontend/src/components/IntentCurationTab.tsx`, `frontend/src/App.tsx`
- **Bố cục Data Ingestion**: nút "Crawl Social Data" + "View Results" dời vào trong cột Social Crawl (dùng `mt-auto` đẩy xuống đáy); "Run Intent Discovery" thành nút chính **căn giữa**, chạy trên toàn bộ nguồn trong scope, kèm dòng helper làm rõ phạm vi.
  `frontend/src/components/DataIngestionTab.tsx`
- **Select-all ở Intent Curation chỉ áp cho tab đang xem** (`visibleIntents`), không chọn nhầm intent ở tab khác. `onToggleSelectAll` đổi chữ ký nhận `ids[]`.
  `frontend/src/components/IntentCurationTab.tsx`, `frontend/src/App.tsx`
- **OperationConsole sang theme sáng** (nền trắng, chữ stone, màu nhãn đậm hơn -400 → -600) + **thanh progress indeterminate** trượt liên tục thay cho thanh % (vì không biết trước thời lượng async op).
  `frontend/src/components/OperationConsole.tsx`, `frontend/src/index.css`

### Added — Tính năng mới
- **Hỗ trợ PRD dạng PDF**: thêm trích text PDF bằng `pypdf` trong `PRDLoader` (nhánh `.pdf` riêng; PDF scan/ảnh không có text → báo lỗi rõ để chuyển sang .md/.txt). Cho phép `.pdf` ở ô upload PRD (`accept` + nhãn). Trước đây upload PDF bị decode như văn bản → ra rác nhị phân → **discover intents fail**.
  `backend/src/ingestion/prd_loader.py`, `frontend/src/components/DataIngestionTab.tsx` · (cài `pypdf` vào `.venv`)

### Fixed — Sửa lỗi
- **PRD (và file/crawl/text đã nhập) bị mất khi chuyển tab rồi quay lại**: Data Ingestion trước đây render theo điều kiện `currentStep === 1` → **unmount khi rời tab**, xoá state cục bộ (PRD upload nhưng chưa ingest, staged files, stats, kết quả crawl, text dán). Nay **giữ tab luôn mounted, chỉ ẩn bằng CSS** khi off-tab → state sống qua các lần chuyển tab.
  `frontend/src/App.tsx`
- **Trạng thái PRD hiển thị nhầm ở khu vực "Documents & Raw Text"**: khối tóm tắt ingest liệt kê cả PRD (dòng `prd ...: 0` + "PRD loaded") ngay trong mục Documents, dù PRD đã có ô status riêng. Nay **lọc PRD khỏi khối Documents** (chỉ hiện source non-PRD, ẩn hẳn nếu không có), và đưa số chars của PRD vào chính **ô PRD** ("PRD loaded · N chars", chỉ khi PRD là nguồn duy nhất để không gán nhầm chars của document/text).
  `frontend/src/components/DataIngestionTab.tsx`

## [Chưa phát hành] — 2026-06-30 (nhánh `feat/intent-merge-cite`) — Keyword coverage

Làm lại bộ keyword mặc định mỗi domain để **độ phủ nhu cầu người dùng** rộng hơn khi crawl social.

### Added — Tính năng mới
- **Prompt sinh keyword** (`backend/src/prompts/keyword_gen.txt`): sinh 10 keyword/domain phủ 7 facet (đặt-mua, giá, chất lượng, hỗ trợ, hoàn-hủy, sự cố, review), 5 cái đầu là bộ "lõi". Chạy offline 1 lần để dựng list rồi ghi cứng — không gọi lúc run app.

### Changed — Thay đổi
- **Keyword mỗi domain (Data Ingestion)**: thay 6 hashtag phẳng (thiên địa danh) bằng **10 keyword phủ facet**, trong đó **5 keyword "lõi" được chọn sẵn**, 5 cái còn lại hiển thị ở mục Suggested để bấm thêm. Áp dụng cho cả 6 preset lẫn custom domain (`CUSTOM_DOMAIN_TAGS`). Tách `getRecommendedTags` (hiện cả 10) khỏi keyword active (chỉ 5 lõi qua `slice(0, CORE_KEYWORD_COUNT)`).
  `frontend/src/components/DataIngestionTab.tsx`

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
