# PRD — Trợ lý AI Hỗ trợ Khách hàng (VOLTA Assistant)

**Sản phẩm:** Chatbot AI hỗ trợ chủ xe điện sau bán hàng
**Công ty:** VOLTA Việt Nam *(tên minh hoạ — thay bằng công ty của bạn)*
**Phiên bản:** PRD v1.0 — phạm vi MVP
**Người viết:** [Tên] · **Ngày:** [Ngày]
**Tóm tắt 1 câu:** Một trợ lý AI trả lời 24/7 các câu hỏi vận hành xe điện (sạc, pin, bảo hành) từ kho tài liệu chính thức, biết tự chuyển sang nhân viên khi gặp vấn đề an toàn hoặc khi không đủ tự tin.

---

## 1. MVP Boundary Sheet

### Riskiest Assumption (giả định nguy hiểm nhất)
> Chủ xe sẽ **tin và dùng** trợ lý AI để tự giải quyết câu hỏi vận hành, **và** AI trả lời đủ chính xác từ kho tài liệu hiện có để giảm tải tổng đài — mà **không bịa** ra thông tin sai về pin/sạc/an toàn.

Nếu giả định này sai (AI trả lời sai nhiều, hoặc khách vẫn thích gọi hotline), toàn bộ giá trị "giảm tải + tự phục vụ" sụp đổ → đây là thứ phải test trước tiên.

### In-Scope (tối đa 3 — mỗi cái map về 1 Need cụ thể)

| # | Tính năng | Need từ chủ xe | Test giả định gì |
|---|---|---|---|
| 1 | **Hỏi–đáp vận hành bằng RAG** trên kho tài liệu chính thức (sạc, pin, tính năng xe, chính sách bảo hành), có **trích nguồn** mỗi câu trả lời | "Tôi cần câu trả lời đúng, ngay, lúc 11h đêm — không muốn chờ tổng đài" | AI có giải quyết đủ chính xác & khách có chịu dùng không (giả định rủi ro nhất) |
| 2 | **Graceful Handover** sang tổng đài viên — chuyển nguyên transcript, không bắt khách kể lại từ đầu | "Khi vấn đề phức tạp/liên quan an toàn, tôi cần gặp người thật mượt mà" | Có thể vận hành **an toàn**; đo được khi AND thất bại |

> **Killer feature** = In-Scope #1. Nếu sản phẩm chỉ làm được một việc, thì đó là *trả lời đúng câu hỏi vận hành tức thì*. #2 phục vụ và bảo vệ #1.

### Out-of-Scope (tốt, nhưng không cần cho MVP)
- **Tư vấn bán hàng / báo giá / chốt đơn mua xe (pre-sales):** hành trình khách khác hẳn, đo bằng metric khác.
- **Cá nhân hoá theo dữ liệu xe real-time** (trạng thái pin/quãng đường của *chính chiếc xe đó* qua telematics): cần tích hợp nặng, để pha 2.
- **Giọng nói / tổng đài thoại (voice bot):** MVP chỉ làm text chat.
- **Đa ngôn ngữ:** chỉ tiếng Việt trước.
- **Xử lý khiếu nại / bồi thường / hoàn tiền tự động:** rủi ro pháp lý cao.

### Non-Goals (ranh giới đỏ — tuyệt đối không làm ở giai đoạn này)
- AI **không bao giờ** đưa ra khẳng định an toàn–kỹ thuật kiểu *"xe bạn vẫn an toàn để lái tiếp"* → luôn handover.
- AI **không** xử lý tình huống khẩn cấp/cứu hộ/tai nạn/pin phồng–cháy → chuyển ngay hotline khẩn cấp.
- AI **không** tự thực hiện giao dịch tài chính (thanh toán, hoàn tiền, trừ tiền).
- AI **không** hứa hẹn nội dung bảo hành/pháp lý nằm ngoài tài liệu chính thức.

*(Kill-check: Non-Goals #2 "cứu hộ tự động" đúng là thứ team rất muốn làm để "wow" — nhưng cố tình loại ra. Non-Goals thật.)*

---

## 2. PRD Skeleton

### 2.1 Problem Statement
> Chủ xe điện VOLTA gặp nhiều câu hỏi vận hành lặp lại (sạc ở đâu, sạc bao lâu, đèn báo lỗi nghĩa là gì, bảo hành pin ra sao), nhưng tổng đài chỉ trực giờ hành chính và quá tải giờ cao điểm — **15–20% câu hỏi bị trả lời chậm hoặc nhỡ**, kéo CSAT xuống và đẩy chi phí mỗi cuộc hỗ trợ lên cao. Mỗi câu hỏi không được giải quyết kịp là một trải nghiệm xấu với một tài sản khách vừa bỏ vài trăm triệu để mua.

### 2.2 Target User
> **Anh Minh, 34 tuổi**, chủ xe VOLTA được ~6 tháng, đi làm hàng ngày bằng xe. Không rành kỹ thuật. Phần lớn thắc mắc xảy ra **ngoài giờ hành chính** (tối, cuối tuần) ngay tại trụ sạc hoặc trong gara nhà. Quen tự tra Google/Zalo trước khi gọi điện, chỉ gọi hotline khi bí thật sự.
>
> *(Nối thẳng từ Customer Segment Card Day 16 — "chủ xe đã mua, dùng hàng ngày", không phải "mọi người dùng xe điện".)*

### 2.3 User Stories
**Story 1 — Tự phục vụ tức thì**
> As a **chủ xe điện đang ở trụ sạc lúc 10h tối**, I want **hỏi vì sao xe sạc chậm và được hướng dẫn xử lý kèm trích nguồn từ sổ tay**, so that **tôi tự khắc phục được mà không phải chờ tổng đài mở cửa sáng hôm sau**.

**Story 2 — Chuyển tiếp an toàn**
> As a **chủ xe gặp cảnh báo nghi liên quan an toàn (mùi khét, đèn cảnh báo pin)**, I want **được trợ lý nhận diện là tình huống rủi ro và chuyển ngay sang nhân viên kèm toàn bộ nội dung đã trao đổi**, so that **tôi được người có chuyên môn xử lý ngay, không phải kể lại từ đầu và không bị AI phỏng đoán sai**.

### 2.4 AI-Specific Section

#### Thành phần 7 — Model Selection Rationale
**Kiến trúc 2 lớp (router + generator), không fine-tune ở MVP:**

- **Lớp phân loại ý định + guardrail (model nhỏ, rẻ — vd Haiku / mini-class):** phân loại câu hỏi và phát hiện nhóm rủi ro cao (an toàn/khẩn cấp/tài chính/pháp lý) trước khi sinh câu trả lời. Rẻ + nhanh vì chạy ở mọi lượt.
- **Lớp sinh câu trả lời có RAG (model mạnh hơn — vd Claude Sonnet / GPT-4o-class):** tổng hợp câu trả lời từ tài liệu retrieved, tiếng Việt tốt, context window đủ lớn để nhét nhiều đoạn tài liệu.

| Trade-off | Quyết định |
|---|---|
| Accuracy vs Cost | Chấp nhận trả nhiều hơn cho model mạnh ở lớp **sinh** (vì sai về pin/sạc là rủi ro an toàn), nhưng tiết kiệm ở lớp **phân loại** bằng model rẻ. |
| Latency | Mục tiêu first-token < ~3s cho trải nghiệm chat. Streaming từng phần. |
| Context window | Cần đủ để nhét 5–8 đoạn tài liệu retrieved + lịch sử phiên. |
| **RAG vs Fine-tune** | **Chọn RAG.** KB thay đổi liên tục (chính sách bảo hành mới, trạm sạc mới) → RAG cho phép cập nhật **không cần train lại**. Fine-tune chỉ cân nhắc sau, để chỉnh tone/format. |
| Privacy/Compliance | **Mask PII** (biển số, số khung, SĐT) trước khi gửi lên API; ưu tiên provider cam kết không lưu dữ liệu (zero-retention). |

- **Trade-off chấp nhận:** dùng cloud API thay vì self-host model → ra mắt nhanh hơn, đánh đổi một phần kiểm soát hạ tầng.
- **Trade-off KHÔNG chấp nhận:** gửi PII thô lên model; để model sinh câu trả lời an toàn–kỹ thuật mà không qua lớp guardrail.

#### Thành phần 8 — Data Requirements
- **Nguồn dữ liệu:**
  - KB nội bộ (→ vector DB): sổ tay sử dụng xe, chính sách bảo hành, FAQ chính thức, bảng mã lỗi & hướng dẫn xử lý.
  - API live-chat/ticketing — để handover.
  - *(Tuỳ chọn)* API mạng lưới trạm sạc — vị trí/trạng thái/giá.
- **Owner:** Phòng Chăm sóc khách hàng sở hữu KB & FAQ; Phòng Kỹ thuật sở hữu tài liệu kỹ thuật & bảng mã lỗi; IT sở hữu ticketing API.
- **Freshness:** KB cập nhật theo sự kiện khi có chính sách mới + rà soát định kỳ hàng tháng; trạng thái trạm sạc near-real-time.
- **Quality control:** 1 CS Lead chịu trách nhiệm duyệt nội dung KB. **Mọi câu trả lời AI phải trích nguồn** về tài liệu gốc để audit và để khách tự kiểm chứng.

#### Thành phần 9 — Fallback UX
**Chiến lược chính: Graceful Handover** (vì miền có rủi ro an toàn/pháp lý cao), **kèm Expectation Management** làm nền.

- **Expectation Management (nền):** dưới khung chat luôn hiển thị *"Trợ lý AI có thể trả lời chưa chính xác — với vấn đề an toàn, hãy chọn Gặp nhân viên."* + nút **Gặp nhân viên** luôn hiện.
- **Trigger handover (cụ thể):**
  1. Điểm retrieval/độ tự tin **dưới ngưỡng** (vd similarity < ngưỡng cấu hình, hoặc model tự báo không chắc).
  2. Lớp phân loại gắn nhãn **nhóm rủi ro cao** (an toàn, pin phồng/cháy, tai nạn, pháp lý, tài chính) → handover **bất kể** độ tự tin.
  3. User bấm 👎 hai lần liên tiếp **hoặc** gõ "gặp người thật".
  4. Ngoài giờ trực → tạo ticket + hẹn gọi lại.
- **Hành động hệ thống:** AI **ngừng phỏng đoán**, hiển thị thông báo, **chuyển nguyên transcript** sang tổng đài viên (warm handover) hoặc tạo ticket nếu ngoài giờ.
- **User options:** *Tiếp tục với AI* · *Gặp nhân viên ngay* · *Đặt lịch gọi lại*.

### 2.5 Success Metrics
- **Primary (Actionable) metric — Automated Resolution Rate có cổng CSAT:**
  % phiên được AI giải quyết **trọn vẹn** (không handover **và** không mở lại trong 48h) **VÀ** đạt 👍 / CSAT ≥ 4/5.
- **Ngưỡng thành công:** ≥ **45%** phiên đạt tiêu chí trên, trong **8 tuần** pilot.
- **Guardrail bắt buộc (không đánh đổi):**
  - **0** câu trả lời sai thuộc nhóm an toàn; **100%** intent rủi ro cao được route đúng sang người thật.
  - First-token latency < ~3s; CSAT trung bình ≥ 4/5.
- **Vanity metrics sẽ KHÔNG dùng:** tổng số tin nhắn, tổng số phiên mở chat, thời lượng chat (chat *lâu* ở đây là tín hiệu **xấu**, không phải engagement).

### 2.6 Dependencies & Constraints
- KB phải được số hoá & duyệt trước khi build (phụ thuộc CS + Kỹ thuật).
- API: ticketing/live-chat (handover), telephony (gọi lại), *(tuỳ chọn)* trạm sạc.
- LLM API provider + vector DB.
- **Compliance:** Nghị định bảo vệ dữ liệu cá nhân (PDPD) — cần consent của khách + cơ chế mask PII.
- Cần đội tổng đài viên trực để nhận handover trong khung giờ pilot.
- Ngân sách: cost/conversation có trần; latency budget cố định.
- Timeline: pilot 8 tuần, 1 nhóm chủ xe / 1 khu vực trước khi mở rộng.

---

## 3. Hypothesis Table

### Hypothesis 1 — cho In-Scope #1 (RAG Q&A)
> Chúng tôi tin rằng việc cho chủ xe **hỏi–đáp vận hành 24/7 bằng AI có RAG trên kho tài liệu chính thức** sẽ giúp **nhóm chủ xe đã mua** **tự giải quyết các câu hỏi thường gặp về sạc/pin/bảo hành mà không cần gọi tổng đài**. Chúng tôi sẽ biết mình đúng khi thấy **Automated Resolution Rate (có cổng CSAT) ≥ 45%** trong vòng **8 tuần**.

- **Riskiest assumption phía sau:** KB hiện tại **đủ đầy** và RAG **đủ tốt** để trả lời chính xác phần lớn câu hỏi thật — và khách **chịu dùng** chat thay vì gọi.
- **Cách test rẻ nhất (Wizard-of-Oz / Concierge):** *Trước khi build full*, cho nhân viên CS trả lời qua một khung chat, **dùng đúng KB + công cụ tìm kiếm nội bộ**, trong 1–2 tuần. Mục tiêu đo: (a) % câu hỏi trả lời được **chỉ từ KB hiện có**, (b) khách có chịu dùng chat không, (c) **thu thập câu hỏi thật** để dựng test-set đánh giá retrieval. Có dữ liệu này rồi mới build RAG.

### Hypothesis 2 — cho In-Scope #2 (Graceful Handover)
> Chúng tôi tin rằng **warm handover (chuyển nguyên transcript)** sẽ giúp **khách ở tình huống phức tạp/an toàn** được xử lý **an toàn và nhanh hơn**. Chúng tôi sẽ biết mình đúng khi thấy **100% intent rủi ro cao được route đúng** và **thời gian xử lý trung bình (AHT) của tổng đài viên giảm ≥ 15%** nhờ có sẵn ngữ cảnh.

- **Riskiest assumption:** lớp phân loại nhận diện đúng nhóm rủi ro cao với recall đủ cao (bỏ sót = nguy hiểm).
- **Cách test rẻ nhất:** chạy classifier trên log câu hỏi thật từ Hypothesis 1, cho CS Lead chấm tay recall/precision nhóm rủi ro cao trước khi đưa vào luồng live.

---

## 4. PMF Scorecard

- **Aha Moment (hành vi cụ thể, không phải cảm giác):**
  > Chủ xe **nhận câu trả lời đúng cho vấn đề vận hành đầu tiên trong < 1 phút** và **không phải gọi tổng đài cho vấn đề đó trong 7 ngày sau**. *(Magic number ứng viên: giải quyết thành công ≥ 2 vấn đề trong 30 ngày đầu → nhóm "retained".)*

- **Actionable Metric:** Automated Resolution Rate (có cổng CSAT) + **tỉ lệ quay lại dùng chatbot cho vấn đề tiếp theo** (reuse) thay vì gọi hotline.

- **PMF Method (kết hợp 2 cách):**
  1. **Sean Ellis Test (40% rule):** hỏi nhóm chủ xe đang dùng *"Bạn sẽ thấy thế nào nếu không còn trợ lý này?"* — mục tiêu **> 40% "Rất thất vọng"**.
  2. **Retention/Reuse curve:** % chủ xe quay lại dùng chatbot cho vấn đề kế tiếp theo cohort — tìm điểm **flatten** (D30 reuse) làm tín hiệu PMF.

- **Vanity metrics sẽ KHÔNG dùng:** tổng tin nhắn, tổng lượt mở chat, tổng thời lượng chat.

---

## 5. Mục để bạn tự bổ sung (theo template Day 17)
- **AI Critique Log:** sau khi chạy phần §4 (Prompts) của handbook để AI phản biện PRD này, ghi lại Issue → Accept/Reject/Partial → lý do.
- **Self-assessment:** mắt xích yếu nhất trong [MVP Boundary → PRD → Hypothesis → PMF] của bạn là gì?
