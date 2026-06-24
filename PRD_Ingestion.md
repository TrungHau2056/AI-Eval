# PRD — Multi-Source Ingestion & Noise Filtering for Intent Detection

**Parent product:** AI Test Case Generator (xem [PRD_MVP.md](PRD_MVP.md))
**Document status:** Draft for Tech Lead review
**Audience:** Tech Lead / Engineering / Stakeholder
**Vai trò tài liệu:** Đây là **bản PRD — *why / what*** (alignment + tổng quan). Toàn bộ chi tiết *how* (FR đánh số, API contract, normalizer params, build sequencing, acceptance, open questions) nằm ở **[PRD_Ingestion_TechSpec.md](PRD_Ingestion_TechSpec.md)** — đó là nguồn sự thật cho engineer khi code.
**Mục đích:** Mở rộng năng lực Input — đưa **"Crawl data từ social/web + xử lý đa nguồn"** (vốn là *Out-of-Scope* của MVP, [PRD_MVP.md:29](PRD_MVP.md)) thành tính năng chính thức, để intent được sinh từ **dữ liệu thật, đa nguồn, đã lọc sạch**.

---

## 0. Bức tranh tổng thể (đọc trước — dành cho Tech Lead)

Feature chia **3 phase**, PRD này **commit Phase 1 (A+B)**, mô tả C ở mức north-star để không khóa cứng tương lai.

| Phase | Tên | Nội dung | Trạng thái |
|---|---|---|---|
| **A** | Multi-format Ingestion | Loader đọc mọi nguồn/định dạng → 1 common format (`RawInput`) | ✅ In-Scope (now) |
| **B** | Normalize & Noise Filtering | Lọc rác, dedup, PRD-as-guidance, merge nguồn | ✅ In-Scope (now) |
| **C** | Semantic Dedup & Clustering | Embedding + cluster cho social volume lớn; tích hợp API Apify live-crawl | 🔜 Future (chỉ chừa hook) |

**Luồng end-to-end:**
```
[Apify cào social] ─┐
[survey files]      ─┼→ A: Loader → RawInput → B: Normalize/dedup/merge → IntentAgent → Intents
[PRD file]          ─┤        (PRD tách ra làm guidance, không mine)
[text dán tay]      ─┘
```
Acquisition (Apify) đứng **ngoài hệ thống**; mọi nguồn vào đều quy về `RawInput` rồi tái dùng nguyên pipeline detect intent hiện có (không sửa `SYSTEM_PROMPT`).

---

## 1. Problem Statement
MVP hiện chỉ nhận **paste text hoặc 1 file CSV** ([PRD_MVP.md:19](PRD_MVP.md)); crawl & đa nguồn bị để ngoài scope. Thực tế Researcher cần gom intent từ **nhiều nguồn dị thể cùng lúc**: comment social (fb/tiktok/threads), kết quả survey (xlsx/csv/json/md/txt), và tài liệu PRD làm ngữ cảnh. Hệ quả khi thiếu năng lực này:
- Phải convert/dán thủ công từng nguồn → tốn thời gian, dễ sót.
- Data social thô **nhiễu & trùng lặp nặng** → intent rác, lệch.
- Không có cách đưa **ngữ cảnh sản phẩm (PRD)** vào để định hướng intent → intent chung chung, sai thuật ngữ domain.
- Kỹ thuật: entry point `POST /api/discover` chỉ nhận text; frontend `readAsText` → **xlsx/binary và social không chạy được**.

## 2. Target User
- **AI Product Researcher / Prompt Engineer / QA** (kế thừa [PRD_MVP.md:16](PRD_MVP.md)) — người nạp data thật để hệ thống bóc intent.
- **Engineering (Tech Lead)** — người cần kiến trúc đủ mở để thay tool cào / thêm nguồn mà không đập lại pipeline.

## 3. User Stories
- **US1 (Đa định dạng):** Là Researcher, tôi muốn upload **nhiều file** nhiều định dạng (xlsx/csv/json/md/txt) cùng lúc, để gộp kết quả survey mà không phải convert thủ công.
- **US2 (Social):** Là Researcher, tôi muốn nạp data social (export từ **Apify** cho fb/tiktok/threads), để intent phản ánh đúng *voice-of-customer* thật.
- **US3 (PRD context):** Là Researcher, tôi muốn đính kèm file PRD làm **ngữ cảnh**, để intent bám đúng thuật ngữ/giai đoạn sản phẩm — *mà bản thân PRD không bị biến thành intent*.
- **US4 (Lọc nhiễu):** Là Researcher, tôi muốn hệ thống **tự dọn rác & khử trùng lặp** trước khi detect, để intent chất lượng hơn, không lặp.
- **US5 (Pluggability):** Là Engineer, tôi muốn tool acquisition (Apify) nằm sau **một adapter**, để sau này đổi tool cào hoặc chỉ dán đại text chỉ phải sửa **1 loader**, không đụng pipeline.

## 4. MVP Scope (Ranh giới)
| | Chi tiết |
|---|---|
| **In-Scope (Phase A+B)** | • Endpoint `POST /api/ingest` (multipart) nhận nhiều file + nhãn nguồn.<br>• Loaders: Excel, JSON, Markdown/Text, **SocialLoader** (đọc export Apify JSON/CSV), **PRDLoader**.<br>• `normalizer`: strip boilerplate, bỏ dòng rỗng/ngắn, **dedup exact-duplicate**, lọc ngôn ngữ; `merge_sources` gộp có nhãn nguồn.<br>• PRD → `state.raw_prd_guidance` (guidance, không vào content).<br>• Frontend đa-file + upload `FormData` server-side.<br>• Giữ nguyên luồng paste-text. |
| **Out-of-Scope (để Phase C / sau)** | • Embedding + clustering ngữ nghĩa.<br>• Tích hợp **API Apify live-crawl** (Phase 1 chỉ export-rồi-upload thủ công).<br>• Parse DOCX/PDF.<br>• Lưu database / versioning ([PRD_MVP.md:29](PRD_MVP.md)). |
| **Non-Goals** | • Không tự cào lén/bypass ToS nền tảng — acquisition do user chủ động chạy Apify.<br>• Không thay tư duy Researcher; vẫn human-in-the-loop. |

## 5. Success Metrics
- **Multi-source coverage:** % intent có evidence trải trên ≥2 nguồn (không dồn 1 nguồn).
- **Noise reduction:** tỉ lệ dòng bị loại ở bước normalize (dedup + rác) — kỳ vọng cắt đáng kể với social.
- **Adoption (kế thừa MVP):** % intent AI sinh được giữ nguyên / sửa nhỏ (<20% text) trước Export.
- **Time-to-value:** giảm thời gian từ "có data đa nguồn thô" → "bộ intent chuẩn".
- **Pluggability (NFR-metric):** thêm/đổi nguồn = **1 file loader mới, 0 thay đổi pipeline**.

## 6. Dependencies & Constraints
- **Dependencies:** LLM API key (Gemini/GPT — kế thừa MVP); `pandas` + **`openpyxl`** (đọc xlsx); **Apify** (acquisition, ngoài hệ thống) cho social.
- **Constraints:**
  - Apify là **SaaS bên thứ 3** → data target gửi ra ngoài, **có phí per Actor run**, chịu ToS fb/tiktok/threads → cân nhắc PII/compliance.
  - Context window LLM → tái dùng chunking sẵn có (`chunk_max_tokens=50000`).
  - API rate limit khi data lớn.

---

## Các thành phần bắt buộc cho AI PRD

## 7. Model Selection Rationale
- **Phase A+B (now):** **không thêm model LLM mới.** Lọc nhiễu là **rule-based** (rẻ, deterministic, dễ test). Detect intent **tái dùng** Gemini 1.5 Pro / GPT-4o như MVP ([PRD_MVP.md:45](PRD_MVP.md)) — lý do giữ nguyên: cần suy luận sâu + context window lớn để bóc intent từ data thô đa nguồn.
  - *Trade-off chấp nhận:* lọc rule-based có thể bỏ sót nhiễu tinh vi → bù bằng human-in-the-loop ở bước curation.
  - *Trade-off không chấp nhận:* thêm 1 LLM-pass lọc cho mọi nguồn → tăng chi phí/latency không tương xứng ở MVP.
- **Phase C (future):** cần **embedding model đa ngữ** (vd BGE-m3 / multilingual-e5) cho clustering social; cân nhắc LLM nhẹ chấm cụm Good/Bad (Dial-In LLM, arXiv 2412.09049).

## 8. Data Requirements
- **Nguồn:** (1) Social — export JSON/CSV từ **Apify** (manual, Phase 1); (2) Survey files xlsx/csv/json/md/txt do user upload; (3) PRD md/txt (context).
- **Common format:** mọi nguồn → `RawInput` ([schemas.py:108](backend/src/models/schemas.py#L108)): `content` (text, **bắt buộc**, cái LLM ăn) + `source_type` + `metadata` (bản structured **optional**: author/timestamp/post_id/filename — cho Phase C). Nguồn thiếu field (copy-paste) → để rỗng, **degrade gracefully**. Chi tiết mapping → TechSpec §Common format & §Apify mapping.
- **Quyền sở hữu:** data thuộc user; tool không lưu DB (kế thừa MVP). Apify-side data tuân chính sách Apify.
- **Freshness:** Phase 1 **tĩnh** (upload thủ công). Phase 2 mới live qua API.
- **Quality control:** Researcher chịu trách nhiệm dọn PII trước khi nạp ([PRD_MVP.md:55](PRD_MVP.md)); `normalizer` lo rác/trùng lặp kỹ thuật.

## 9. Fallback UX
**Chiến lược cốt lõi: Human-in-the-loop** (kế thừa [PRD_MVP.md:58](PRD_MVP.md)) + bổ sung fallback riêng cho ingestion:
1. **Ingest Preview/Stats (Expectation Mgmt):** sau `/api/ingest`, hiển thị tóm tắt *(mỗi nguồn nạp bao nhiêu dòng, còn lại sau dedup bao nhiêu)* **trước khi** chạy discover → user thấy đã nạp đúng chưa, gỡ bớt nguồn nếu cần.
2. **Per-file graceful skip:** 1 file lỗi (sai định dạng/corrupt) → **bỏ qua + cảnh báo file đó**, không làm sập cả mẻ.
3. **`data_gap_warning` surfaced:** khi data quá ít, IntentAgent (đã có cơ chế) trả cảnh báo → hiển thị thay vì bịa intent.
4. **Curation gate (giữ nguyên):** Intent sinh ra vẫn vào Data Grid để edit/xóa/regenerate trước khi sang bước Persona.
- **Trigger "AI/ingest không chắc chắn":** file parse ra 0 dòng text hợp lệ; nguồn sau dedup rỗng; `data_gap_warning != null`.

---

## Riskiest Assumption (stress-test trước khi build)
> *"Data social export từ Apify + lọc rule-based đủ sạch để LLM bóc ra intent chất lượng mà chưa cần clustering (C)."*
> Cách test rẻ nhất: chạy 1 mẻ social thật (vài trăm comment) qua A+B → review tỉ lệ intent rác/trùng. Nếu quá cao → ưu tiên kéo Phase C lên sớm.

## ➡️ Chi tiết triển khai
Kiến trúc, FR đánh số, **API contract `/api/ingest`**, **mapping export Apify**, **tham số normalizer**, **build sequencing**, acceptance & open questions → **[PRD_Ingestion_TechSpec.md](PRD_Ingestion_TechSpec.md)**.
