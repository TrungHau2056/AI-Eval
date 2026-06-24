# Day 17 — Sổ tay học viên
## PRD & Product Market Fit
### Builder-to-Product Bridge

> **A great strategy dies in execution if you don't know exactly what to build first.**
> Một chiến lược tuyệt vời vẫn có thể chết gục ở khâu thực thi nếu không biết chính xác phải build gì trước.

---

## 0. Cách dùng sổ tay này

Dùng **trong lúc làm workshop** — không phải để đọc hết một lượt. Mỗi lần bí, mở đúng phần cần:

| Khi bạn cần… | Mở phần… |
|---|---|
| Hiểu mạch logic tổng thể | §1 |
| Đọc nhanh một khái niệm | §2 |
| Điền template workshop | §3 |
| Chạy AI critique PRD | §4 (Prompts) |
| Biết output gì cần có ở mỗi checkpoint | §5 (Checkpoints) |
| Xem tiêu chí chấm điểm & cách submit | §6 (Rubric & Submission) |
| Chuẩn bị bản nộp cuối buổi | §7 (Final submission) |
| Đọc tham khảo sâu hơn | §8 (References) |

**Quy ước ngôn ngữ:** Tiếng Việt ưu tiên. Các **term, công thức, prompt** giữ tiếng Anh để không lệch nghĩa khi làm việc với AI.

---

## 1. Mạch logic Day 17

Day 17 tiếp nối trực tiếp từ Day 16. Nếu Day 16 xây **2 tầng nền** (Market), thì Day 17 xây **4 tầng trên** (Product) của Lean Product Pyramid.

```
         ┌──────────────────────────────────┐
         │         [Day 17]                 │
         │  Tầng 6: Test with Customers     │  ← Workshop 3
         │  Tầng 5: UX & Prototype          │  ← Workshop 2
         │  Tầng 4: Feature Set             │  ← Workshop 1
         │  Tầng 3: Value Proposition       │  ← Workshop 1
         ├──────────────────────────────────┤
         │         [Day 16 — ĐÃ XONG]       │
         │  Tầng 2: Underserved Needs       │
         │  Tầng 1: Target Customer         │
         └──────────────────────────────────┘
                  Lean Product Pyramid
                      — Dan Olsen
```

**Nguyên tắc không đổi:** Không xây nhà từ nóc. Mọi tính năng trong Day 17 phải phục vụ đúng Customer và Need đã xác định ở Day 16.

### Ba workshop và đầu ra

| Workshop | Tầng | Câu hỏi chính | Output |
|---|---|---|---|
| **WS1 — MVP Boundary** | 3 & 4 | Build gì trước, bỏ gì lại? | MVP Boundary Sheet |
| **WS2 — PRD Skeleton** | 5 | Định nghĩa quyết định sản phẩm thế nào? | PRD Skeleton |
| **WS3 — Hypothesis & PMF** | 6 | Đo lường thành công bằng số nào? | Hypothesis Table + PMF Scorecard |

---

## 2. Các khái niệm chính

### 2.1 MVP — Minimum Viable Product

**MVP không phải là sản phẩm bị lột bỏ tính năng.** MVP là **bài test rẻ nhất để mua sự thật từ thị trường**.

> *The goal of an MVP is not to build the smallest product — it's to learn the most with the least effort.*

**3 dạng MVP phổ biến không cần code:**

| Loại MVP | Khi nào dùng | Ví dụ kinh điển |
|---|---|---|
| **Wizard of Oz MVP** | Khi rủi ro lớn nhất là "khách có mua không?" | Zappos (1999): chụp ảnh giày, đăng web, tự đi mua ship |
| **Explainer Video MVP** | Khi rủi ro lớn nhất là "khách có hiểu giá trị không?" | Dropbox (2008): video 3 phút, waitlist từ 5k → 75k người |
| **Landing Page MVP** | Khi rủi ro lớn nhất là "khách có trả tiền không?" | Buffer (2010): bảng giá giả, chờ người click "Mua" rồi mới code |

**Quy tắc vàng:** Trước khi viết code, hãy xác định **giả định rủi ro nhất** (Riskiest Assumption) và tìm cách test nó với chi phí thấp nhất.

---

### 2.2 MVP Boundary — Ranh giới MVP

Ba khái niệm bắt buộc phải xác định trước khi build:

| Khái niệm | Định nghĩa | Tại sao quan trọng |
|---|---|---|
| **In-Scope** | Tính năng cốt lõi bắt buộc phải có để test giả thuyết | Thiếu 1 tính năng này → không test được |
| **Out-of-Scope** | Tính năng tốt, nhưng không cần cho MVP | Làm thêm thứ này = lãng phí thời gian build |
| **Non-Goals** | Ranh giới đỏ — thứ sản phẩm sẽ **không bao giờ** làm (ít nhất trong giai đoạn này) | Giữ focus, tránh scope creep trong team |

**Kill question cho MVP Boundary:**
> *Nếu cắt thêm 1 tính năng nữa trong In-Scope, khách hàng có còn nhận được giá trị cốt lõi không?*
>
> Nếu **CÓ** → tính năng đó phải chuyển sang Out-of-Scope. MVP vẫn đang quá béo.

**Bài học từ các startup nổi tiếng:**
- **Instagram:** Cắt 90% tính năng của Burbn, chỉ giữ lại Chụp ảnh → Filter → Share. Kết quả: tỷ đô.
- **Slack:** Vứt bỏ cả một tựa game (Glitch), chỉ giữ lại công cụ chat nội bộ team vẫn dùng hàng ngày.
- **Figma:** Không cố copy Adobe. Dồn 100% vào đúng 1 tính năng đối thủ không có: Multiplayer realtime.

---

### 2.3 PRD — Product Requirements Document

**PRD là gì:** Văn bản đồng thuận (Alignment Document) về **"Cái gì"** và **"Tại sao"** — không phải "Làm thế nào".

**PRD không phải là:**
- Technical Specification (đó là việc của Engineering)
- Design mockup (đó là việc của Designer)
- Một tài liệu dài hàng chục trang (đối với giai đoạn MVP)

**Ai đọc PRD và đọc để làm gì:**

| Người đọc | Họ cần biết gì từ PRD |
|---|---|
| Engineer | Cần build cái gì, behavior mong muốn là gì |
| Designer | Luồng người dùng (User Flow) trông như thế nào |
| Stakeholder / Investor | Tại sao chúng ta làm thứ này, giá trị là gì |

#### 6 thành phần standard của PRD Skeleton

**1. Problem Statement** — *Bài toán cần giải quyết là gì?*
- Ai đang gặp vấn đề? Tần suất? Tác động kinh tế ước tính?
- Nối trực tiếp từ **Need Map của Day 16**

**2. Target User** — *Ai là người dùng ưu tiên?*
- Nối trực tiếp từ **Customer Segment Card của Day 16**
- Một chân dung cụ thể — không phải "tất cả mọi người"

**3. User Stories** — *Hành vi người dùng trông như thế nào?*
- Công thức: `As a [role], I want [action] so that [outcome]`
- Mỗi User Story là 1 hành vi cụ thể, không phải 1 tính năng
- Ví dụ tốt: *"As a bus operator manager, I want to receive a call summary after AI handles a booking, so that I can review and fix any errors before confirming."*
- Ví dụ kém: *"As a user, I want to use AI features"* (quá chung chung)

**4. MVP Scope** — *Ranh giới build*
- In-Scope / Out-of-Scope / Non-Goals (đã làm ở WS1)

**5. Success Metrics** — *Thế nào là thành công?*
- Gắn trực tiếp với Hypothesis và PMF Scorecard (WS3)
- Phải là Actionable Metric, không phải Vanity Metric

**6. Dependencies & Constraints** — *Ràng buộc cần biết*
- API third-party nào cần gọi?
- Data source nào cần access?
- Timeline, budget constraints?

---

### 2.4 AI PRD — 3 thành phần bổ sung bắt buộc

Khi sản phẩm có AI, PRD cần thêm 3 thành phần mà PRD truyền thống không có:

#### Thành phần 7: Model Selection Rationale

Ghi rõ **tại sao chọn model này** thay vì các model khác. Không được chỉ viết "dùng GPT-4o" mà không có lý do.

Trade-offs cần cân nhắc:

| Yếu tố | Câu hỏi cần trả lời |
|---|---|
| **Accuracy vs Cost** | Model đắt hơn có thực sự cần thiết cho use-case này không? |
| **Latency** | Ứng dụng cần phản hồi trong bao lâu? Real-time hay async? |
| **Context window** | Input của bạn dài bao nhiêu? Model có đủ context không? |
| **Privacy / Compliance** | Dữ liệu có được phép gửi lên cloud không? Có cần on-premise? |
| **Fine-tuned vs RAG** | Cần fine-tune riêng hay RAG từ knowledge base là đủ? |

#### Thành phần 8: Data Requirements

Ghi rõ **dữ liệu lấy từ đâu** để AI hoạt động đúng:

- **Nguồn dữ liệu:** Internal database, external API, user-uploaded, web crawl?
- **Quyền sở hữu:** Ai own data? Ai có quyền update?
- **Freshness:** Dữ liệu cần update theo real-time, daily, hay static?
- **Quality control:** Ai chịu trách nhiệm kiểm tra chất lượng data đầu vào?

#### Thành phần 9: Fallback UX

Đây là **điểm khác biệt lớn nhất** giữa AI PRD và PRD truyền thống.

> *Trong phần mềm truyền thống, nút bấm luôn làm đúng những gì bạn bảo. Trong AI, bạn phải thiết kế cho cả lúc nó làm sai.*

**3 chiến lược Fallback UX:**

**Chiến lược 1 — Quản trị kỳ vọng (Expectation Management):**
Thông báo rõ ràng cho user ngay từ đầu rằng AI có thể sai.
- Ví dụ: ChatGPT ghi "ChatGPT can make mistakes" ngay dưới khung chat.
- Cách dùng: Hiệu quả nhất khi rủi ro sai còn ở mức chấp nhận được (text generation, summarization).

**Chiến lược 2 — Human-in-the-loop:**
AI không tự động thay đổi data thật — luôn cần user xác nhận bước cuối.
- Ví dụ: Notion AI hiển thị kết quả trong khối tạm thời màu tím. User phải bấm "Keep", "Try again", hoặc "Discard".
- Cách dùng: Khi AI có thể thay đổi dữ liệu quan trọng (viết lại văn bản, sửa code, thay đổi cấu hình).

**Chiến lược 3 — Graceful Handover:**
Khi AI không tự tin, hệ thống tự động chuyển quyền kiểm soát về cho con người.
- Ví dụ: Tesla Autopilot cảnh báo và yêu cầu tài xế cầm vô lăng khi mất tín hiệu vạch kẻ đường.
- Cách dùng: Khi rủi ro cao (hệ thống tự lái, y tế, tài chính), hoặc khi confidence score của model dưới ngưỡng.

**Bảng chọn chiến lược Fallback UX:**

| Mức độ rủi ro khi AI sai | Chiến lược phù hợp |
|---|---|
| Thấp (user có thể tự nhận ra lỗi) | Quản trị kỳ vọng |
| Trung bình (AI thay đổi dữ liệu quan trọng) | Human-in-the-loop |
| Cao (ảnh hưởng đến an toàn, tài chính, pháp lý) | Graceful Handover |

---

### 2.5 Hypothesis Testing — Kiểm định giả thuyết

**Mọi tính năng trong PRD đều là một vụ cá cược.** Hypothesis Testing là cách ghi rõ điều kiện thắng/thua của từng cược đó.

**Công thức viết Hypothesis:**
```
Chúng tôi tin rằng [Tính năng / Thay đổi X]
sẽ giúp [Nhóm khách hàng Y]
đạt được [Kết quả Z].
Chúng tôi sẽ biết mình đúng khi thấy [Metric M] đạt [Ngưỡng T].
```

**RAT — Riskiest Assumption Test:**
Trong tất cả các giả định ngầm đằng sau PRD của bạn, hãy tìm ra **cái nguy hiểm nhất** — giả định mà nếu sai thì toàn bộ dự án sụp đổ — và test **nó trước tiên**.

Cách xác định Riskiest Assumption:
1. Liệt kê tất cả giả định đằng sau sản phẩm (user behavior, willingness to pay, technical feasibility...)
2. Với mỗi giả định, hỏi: *"Nếu giả định này sai, dự án có thể vẫn tiếp tục không?"*
3. Giả định mà câu trả lời là **"KHÔNG"** chính là Riskiest Assumption cần test đầu tiên

---

### 2.6 PMF — Product-Market Fit

**PMF không phải là cảm giác.** PMF là khi có đủ bằng chứng định lượng rằng sản phẩm đang giải quyết đúng vấn đề cho đúng người.

#### Ba cách đo PMF

**Cách 1 — Sean Ellis Test (40% Rule):**

Hỏi người dùng hiện tại: *"Bạn sẽ cảm thấy thế nào nếu không còn dùng được sản phẩm này nữa?"*

Các lựa chọn trả lời:
- Very disappointed (Rất thất vọng)
- Somewhat disappointed (Hơi thất vọng)
- Not disappointed (Không thất vọng)
- N/A (Tôi đã không còn dùng rồi)

**Ngưỡng PMF:** Nếu **>40%** trả lời "Very disappointed" → có dấu hiệu PMF.

Cách dùng kết quả để improve PMF (như Superhuman):
- Bỏ qua nhóm "Not disappointed" (họ không phải khách hàng mục tiêu)
- Phân tích nhóm "Very disappointed": họ yêu gì nhất? → Dồn lực vào đó
- Phân tích nhóm "Somewhat disappointed": họ thiếu gì để chuyển sang "Very disappointed"? → Build thứ đó

**Cách 2 — Retention Curve:**

Vẽ đồ thị % người dùng vẫn còn active theo thời gian (cohort analysis).

```
100% ─┐
       │ \
       │   \
  40% ─┤    '────────────────── ← Flattening = PMF signal
       │
   0% ─┴──────────────────────→ Thời gian (ngày/tuần/tháng)
```

- **Đường cong cắm thẳng xuống 0:** Không có PMF. Người dùng thử rồi bỏ hết.
- **Đường cong đi ngang (flatten):** Có PMF. Một tỷ lệ người dùng đã hình thành thói quen.

**Ngưỡng tham khảo:**
- B2C app: D30 retention > 10%
- B2B SaaS: D30 retention > 30%
- Social/viral app: D7 retention > 25%

**Cách 3 — Aha Moment / Magic Number:**

Tìm ra **hành vi cụ thể** mà những người dùng giữ lại lâu dài đều thực hiện trong những ngày đầu.

| Sản phẩm | Magic Number / Aha Moment |
|---|---|
| **Facebook** | Kết bạn với 7 người trong 10 ngày đầu |
| **Twitter** | Follow 30 người |
| **Spotify** | Nghe bài nào đó từ Discover Weekly rồi Save lại |
| **Dropbox** | Upload file đầu tiên và mở nó trên một thiết bị khác |

**Cách tìm Aha Moment cho sản phẩm của bạn:**
1. Chia user thành 2 nhóm: "Retained users" (dùng lâu dài) và "Churned users" (bỏ sớm)
2. So sánh hành vi 7–14 ngày đầu của 2 nhóm
3. Tìm hành vi mà "Retained users" làm nhiều hơn "Churned users" — đó là Aha Moment candidate
4. Verify bằng cách build feature để ép user mới đạt được hành vi đó sớm hơn → đo retention

---

### 2.7 Actionable Metric vs Vanity Metric

**Vanity Metric (Chỉ số ảo):** Con số trông đẹp nhưng không cho biết sản phẩm đang tốt lên hay tệ đi về mặt thực chất.

**Actionable Metric (Chỉ số hành động):** Con số gắn trực tiếp với hành vi tạo ra giá trị — khi con số này tốt lên, product thực sự tốt hơn.

**Test để phân biệt:**
> *Nếu con số này tăng lên mà hành vi cốt lõi không đổi — đó là Vanity Metric.*

| Vanity Metrics ❌ | Actionable Metrics ✅ |
|---|---|
| Số lượt tải app | D30 Retention Rate |
| Tổng lượt đăng ký | % User hoàn thành onboarding |
| Lượt xem trang | Conversion rate từ visit → action |
| Số follower | Engagement rate (reply, share, save) |
| Revenue tổng | Revenue per active user (ARPU) |
| DAU/MAU tổng | DAU/MAU ratio (stickiness) |

**North Star Metric:** Một con số duy nhất phản ánh tốt nhất việc sản phẩm đang tạo ra giá trị cho user. Mọi team đều nên biết North Star của mình.

---

## 3. Workshop toolkits & templates

### 3.1 Workshop 1 — MVP Boundary Sheet

**Thời lượng:** ~50 phút
**Câu hỏi chính:** Build gì trước, bỏ gì lại?

#### Bước 1 — Xác định Killer Feature (5 phút)

Trả lời câu hỏi: *Nếu sản phẩm của tôi chỉ làm được **một thứ** — thứ đó là gì?*

Đây chính là trung tâm của In-Scope. Mọi tính năng khác đều phụ.

#### Bước 2 — Xác định Riskiest Assumption (5 phút)

Trả lời: *Giả định nào, nếu sai, sẽ làm toàn bộ ý tưởng sụp đổ?*

Viết 1 câu rõ ràng: *"Chúng tôi giả định rằng [X]."*

#### Bước 3 — Điền MVP Boundary Sheet (15 phút)

```
MVP BOUNDARY SHEET
══════════════════════════════════════════

Idea (1 câu):
___________________________________________

Riskiest Assumption:
___________________________________________

IN-SCOPE
(Tính năng cốt lõi bắt buộc để test giả thuyết)
→ ___________________________________________
→ ___________________________________________
→ ___________________________________________

OUT-OF-SCOPE
(Tính năng tốt nhưng không cần cho MVP)
→ ___________________________________________
→ ___________________________________________
→ ___________________________________________
→ ___________________________________________

NON-GOALS
(Ranh giới đỏ — tuyệt đối không làm trong giai đoạn này)
→ ___________________________________________
→ ___________________________________________
```

#### Checkpoint 1 — Kill questions:

1. *Nếu cắt thêm 1 tính năng trong In-Scope, khách hàng còn nhận được giá trị cốt lõi không?*
   → Nếu có → tính năng đó thuộc Out-of-Scope.

2. *In-Scope của bạn có nhiều hơn 3 tính năng không?*
   → Nếu có → bạn chưa sắc. Cắt tiếp.

3. *Non-Goals của bạn có ít nhất 1 thứ mà team đang rất muốn làm không?*
   → Nếu không → Non-Goals chưa thật.

---

### 3.2 Workshop 2 — PRD Skeleton

**Thời lượng:** ~55 phút
**Câu hỏi chính:** Định nghĩa quyết định sản phẩm.

#### Bước 1 — Viết Problem Statement (5 phút)

1 câu, dạng: *"[Ai] đang gặp vấn đề [gì] — điều này gây ra [hậu quả kinh tế / vận hành]."*

Ví dụ tốt: *"Nhà xe vừa nhỏ đang mất 15–20% cuộc gọi đặt vé trong giờ cao điểm vì không đủ nhân sự trực tổng đài — mỗi cuộc gọi nhỡ là một lần mất doanh thu."*

#### Bước 2 — Viết 2 User Stories (10 phút)

Dùng công thức: `As a [role], I want [action] so that [outcome].`

Lưu ý:
- [role] = một người thật, cụ thể (không phải "user")
- [action] = hành động trong sản phẩm (không phải "sử dụng tính năng X")
- [outcome] = kết quả business / operational (không phải "để dễ hơn")

#### Bước 3 — Điền AI-specific section (15 phút)

```
AI-SPECIFIC SECTION
══════════════════════════════════════════

MODEL SELECTION
Model dự kiến sử dụng: ____________________
Tại sao chọn model này (không phải model khác)?
→ ___________________________________________
Trade-offs chấp nhận được: ________________
Trade-offs không chấp nhận được: __________

DATA REQUIREMENTS
Nguồn dữ liệu cần thiết: __________________
Ai sở hữu data này? _______________________
Cần update data theo chu kỳ nào? __________
Rủi ro về data quality: ___________________

FALLBACK UX
Chiến lược Fallback: [ ] Expectation Mgmt  [ ] Human-in-the-loop  [ ] Graceful Handover
Trigger khi nào AI bị coi là "không tự tin"? ___________
Khi đó, hệ thống hiển thị / làm gì? ____________________
User có thể override AI không? [ ] Có  [ ] Không
Nếu có, UX cho phép override trông như thế nào? ________
```

#### Bước 4 — Điền Success Metrics và Dependencies (5 phút)

```
SUCCESS METRICS (từ WS3 — điền sau)
Primary metric: ____________________________
Ngưỡng thành công: _________________________

DEPENDENCIES & CONSTRAINTS
API / Service cần tích hợp: ________________
Timeline constraint: ______________________
Budget constraint: _________________________
Legal / Compliance constraint: _____________
```

#### Checkpoint 2 — Kill questions:

1. *Nếu một kỹ sư đọc 2 User Stories này, họ có cần hỏi lại hơn 3 câu để bắt đầu code không?*
   → Nếu có → User Stories còn mơ hồ.

2. *Fallback UX của bạn có mô tả cụ thể trigger và hành động không?*
   → "Khi AI không tự tin" là chưa đủ. Phải là "Khi confidence score < 80% hoặc khi response chứa X pattern."

3. *Model Selection Rationale có giải thích trade-off không?*
   → "Dùng GPT-4o vì nó tốt" là không đủ.

---

### 3.3 Workshop 3 — Hypothesis Table & PMF Scorecard

**Thời lượng:** ~50 phút
**Câu hỏi chính:** Đo lường thành công bằng số nào?

#### Bước 1 — Viết Hypothesis cho mỗi tính năng In-Scope (10 phút)

```
HYPOTHESIS TABLE
══════════════════════════════════════════

Tính năng: ________________________________

Hypothesis:
"Chúng tôi tin rằng [tính năng này]
sẽ giúp [nhóm khách hàng]
đạt được [kết quả cụ thể].
Chúng tôi sẽ biết mình đúng khi thấy
[metric] đạt [ngưỡng cụ thể]
trong vòng [thời gian]."

Riskiest Assumption phía sau hypothesis này:
→ ___________________________________________

Cách test assumption này với chi phí thấp nhất:
→ ___________________________________________
```

#### Bước 2 — Xác định Aha Moment (10 phút)

Trả lời 3 câu hỏi:
1. *Khoảnh khắc nào khiến user lần đầu tiên thực sự "thấy" giá trị của sản phẩm?*
2. *Hành vi nào trên sản phẩm phản ánh khoảnh khắc đó?*
3. *Làm sao đo lường hành vi đó?*

#### Bước 3 — Điền PMF Scorecard (10 phút)

```
PMF SCORECARD
══════════════════════════════════════════

Aha Moment (mô tả hành vi cụ thể):
→ ___________________________________________

Actionable Metric đo Aha Moment:
→ ___________________________________________
(Không dùng: số downloads, lượt view, sign-ups)

Phương pháp đo PMF sẽ dùng:
[ ] Sean Ellis Test — ngưỡng: >40% "Very disappointed"
[ ] Retention Curve — ngưỡng: D30 > ____%
[ ] Aha Moment tracking — ngưỡng: ___% user đạt trong ___ ngày
[ ] Khác: _______________________________

Thời điểm đo PMF lần đầu: ________________
(Phải đủ dữ liệu — thường 4–8 tuần sau launch)

Vanity Metrics tôi sẽ KHÔNG dùng để tự lừa:
→ ___________________________________________
→ ___________________________________________
```

---

## 4. Prompts cho Vibe Coding (English-only)

> **Lưu ý:** Giống Day 16, tất cả prompt giữ tiếng Anh 100% để AI giữ ngữ nghĩa ổn định. Thảo luận kết quả bằng tiếng Việt.

### 4.1 PRD Stress-Test Prompt (Prompt chính — dùng cuối WS3)

Dùng sau khi đã có cả 3 tài liệu: MVP Boundary + PRD Skeleton + Hypothesis.

```
Act as a ruthless Lead Product Manager and a skeptical Senior AI Engineer.
Review my MVP Boundary, PRD Skeleton, and Hypothesis provided below.

Do NOT rewrite them. Perform a stress test instead:

1. SCOPE CREEP
   Identify any "In-Scope" features that are actually "Nice-to-haves"
   and should be moved to "Out-of-Scope".
   For each, explain why it is not essential to test the core hypothesis.

2. AI FALLBACK HOLES
   Point out edge cases where my AI model might fail, hallucinate,
   or cause user frustration that I have not accounted for in my Fallback UX.
   Be specific about the scenario and the missing UX response.

3. VANITY METRIC TRAP
   Critique my chosen Aha Moment metric.
   Is it truly actionable, or is it a vanity metric in disguise?
   If it is a vanity metric, suggest a better leading indicator.

4. HYPOTHESIS WEAKNESS
   Identify which hypothesis has the weakest evidence base.
   What is the easiest way to invalidate it?

Be direct, highly critical, and provide specific examples for your critiques.
Do not be encouraging. Find the problems.

[Paste: MVP Boundary + PRD Skeleton + Hypothesis Table here]
```

**Cách dùng:**
1. Paste toàn bộ 3 tài liệu vào cuối prompt
2. Đọc từng điểm AI chỉ ra
3. Với mỗi điểm: **accept** (sửa theo), **reject** (giữ, có lý do), hoặc **partial**
4. Mọi sửa đổi phải do **bạn viết lại** — không copy câu rewrite của AI nguyên văn

---

### 4.2 User Story Rewrite Prompt

Dùng khi User Story còn mơ hồ hoặc viết theo dạng feature (không phải hành vi).

```
Evaluate this User Story and improve it.

User Story: [paste here]

Check:
1. Is the role specific enough (a real person, not "user")?
2. Is the action a behavior in the product (not "use feature X")?
3. Is the outcome a business or operational consequence (not just "easier")?

If any part is weak, rewrite the full User Story following the format:
"As a [specific role], I want [specific action in the product],
so that [measurable business/operational outcome]."

Do not invent facts not present in the original.
```

---

### 4.3 Fallback UX Design Prompt

Dùng khi cần thiết kế Fallback UX cho một scenario cụ thể.

```
I am building an AI product with the following context:
- Product type: [describe]
- AI capability: [what the AI does]
- Target user: [who uses it]
- Risk level if AI is wrong: [low / medium / high]

Design the Fallback UX for this specific failure scenario:
"[describe the scenario where AI might fail or be uncertain]"

For the fallback, specify:
1. What triggers the fallback (confidence threshold, error type, etc.)
2. What the user sees or hears at that moment
3. What action options the user has
4. How the system recovers gracefully

Choose the appropriate fallback strategy:
Expectation Management / Human-in-the-loop / Graceful Handover

Explain why you chose that strategy given the risk level.
```

---

### 4.4 PMF Metric Validation Prompt

Dùng để kiểm tra xem Metric mình chọn có thực sự đo được PMF không.

```
I am building a product in [industry/domain].
My target user is: [describe]
My core value proposition is: [describe]

I am considering using this metric to measure PMF:
"[your proposed metric]"

Evaluate this metric:
1. Is this an actionable metric or a vanity metric? Explain why.
2. Does this metric directly reflect the moment users experience core value?
3. What user behavior could inflate this metric without real value being delivered?
4. Suggest one alternative metric that would be harder to game and more directly
   tied to the user receiving genuine value.

If you recommend an alternative, show how to calculate it from available data.
```

---

### 4.5 Hypothesis Stress-Test Prompt

Dùng khi muốn tìm điểm yếu của Hypothesis trước khi build.

```
Review this product hypothesis:

"We believe that [feature/change X]
will help [customer segment Y]
achieve [outcome Z].
We will know we are right when [metric M] reaches [threshold T]."

Stress test it by answering:
1. What is the single riskiest assumption hidden in this hypothesis?
2. Under what realistic conditions would this hypothesis be FALSE?
3. Is the success metric truly measurable with the data we likely have access to?
4. Suggest the cheapest possible experiment to validate the riskiest assumption
   before building the full feature.

Be adversarial. Try to break the hypothesis.
```

---

## 5. Checkpoints — Output yêu cầu

### 5.1 Checkpoint 1 — Scope Review Gate

**Khi nào:** Sau Workshop 1
**Output cần có:** MVP Boundary Sheet đã điền đầy đủ 3 cột

**Pass signals:**
- In-Scope có tối đa 3 tính năng
- Mỗi tính năng In-Scope đều có thể map trực tiếp về 1 Need từ Day 16
- Out-of-Scope dài hơn In-Scope (chứng tỏ đã thực sự cắt)
- Non-Goals có ít nhất 1 thứ team đang rất muốn làm

**Fail signals:**
- In-Scope có hơn 5 tính năng
- Không thể trả lời được: *"Tính năng này test giả định gì?"*
- Non-Goals trống hoặc chỉ có những thứ không ai muốn làm

---

### 5.2 Checkpoint 2 — Clarity Review Gate

**Khi nào:** Sau Workshop 2
**Output cần có:** PRD Skeleton đầy đủ 9 thành phần (6 standard + 3 AI-specific)

**Pass signals:**
- User Stories có thể đọc và hiểu mà không cần giải thích thêm
- Fallback UX có trigger cụ thể và hành động cụ thể
- Model Selection có lý do và trade-off rõ ràng
- Data Source có tên cụ thể (không phải "từ internet")

**Fail signals:**
- User Story viết theo kiểu feature: *"As a user, I want AI to work"*
- Fallback UX chỉ có: *"Hiện thông báo lỗi"*
- Model Selection chỉ ghi tên model, không có lý do
- Dependencies trống

---

### 5.3 Final Checklist — Trước 13:00

```
[ ] 1. MVP Boundary Sheet — In-scope, Out-of-scope, Non-goals
[ ] 2. PRD Skeleton — 6 thành phần standard + 3 AI-specific
[ ] 3. Hypothesis Table — ít nhất 1 hypothesis per In-Scope feature
[ ] 4. PMF Scorecard — Aha Moment + Actionable Metric + PMF method
[ ] 5. PRD đã qua AI Stress-Test và được chỉnh sửa ít nhất 1 lần
```

**Minimum bar:** Nếu một kỹ sư đọc PRD của bạn, họ phải hiểu được: build cái gì, tại sao, AI làm gì khi sai, và thành công trông như thế nào — **mà không cần hỏi lại hơn 3 câu**.

---

## 6. Rubric & Submission

### 6.1 Cách nộp bài — 2 phiên bản bắt buộc

| | Phiên bản A — End-of-session | Phiên bản B — BTVN |
|---|---|---|
| **Nộp khi nào** | Cuối buổi sáng Day 17 (trước 13:00) | Trước 23:59 cùng ngày Day 17 |
| **Nộp ở đâu** | Submit trực tiếp trên LMS | Submit **link public GitHub** lên LMS |
| **Bao gồm** | MVP Boundary + PRD Skeleton + Hypothesis/PMF (bản nháp) | Bản hoàn chỉnh hơn trong `submission.md` trên GitHub |

> **Lưu ý:** Phiên bản A là snapshot tư duy tại thời điểm cuối buổi. Không chỉnh A sau khi đã nộp — A dùng để đo mức độ cải thiện sang B.

---

### 6.2 Rubric — 100 điểm, 5 tiêu chí

| # | Tiêu chí | Điểm | Chấm ở đâu |
|---|---|---:|---|
| 1 | **Product Judgment** | 35 | Chủ yếu B, đối chiếu A |
| 2 | **AI Design Rigor** | 20 | Chủ yếu B |
| 3 | **Measurement Quality** | 15 | B |
| 4 | **Story Consistency** | 10 | B, tham chiếu Day 16 |
| 5 | **Iteration Quality** | 20 | So sánh A vs B |

---

**Tiêu chí 1 — Product Judgment (35 điểm)**

Mức độ sắc bén của toàn bộ product logic: MVP Boundary có thực sự cắt đến mức cần thiết chưa? In-Scope có đủ focused không? Non-Goals có thực sự là ranh giới đỏ không? PRD có phản ánh đúng Customer và Need từ Day 16 không?

*Điểm cao nhất dành cho bài có thể trả lời: "Tại sao mỗi tính năng trong In-Scope là bắt buộc và không thể cắt thêm."*

---

**Tiêu chí 2 — AI Design Rigor (20 điểm)**

Chấm chất lượng của 3 thành phần AI-specific trong PRD. Model Selection Rationale có giải thích trade-off thực sự không, hay chỉ ghi tên model? Data Requirements có xác định được nguồn cụ thể không? Fallback UX có trigger và hành động cụ thể không, hay chỉ là "hiện thông báo lỗi"?

*Tiêu chí này phân biệt người hiểu AI product design với người chỉ copy template.*

---

**Tiêu chí 3 — Measurement Quality (15 điểm)**

Hypothesis có viết đúng công thức không? Aha Moment có được xác định bằng hành vi cụ thể không? Metric được chọn có thực sự là Actionable Metric không, hay là Vanity Metric ngụy trang? PMF method có phù hợp với loại sản phẩm không?

---

**Tiêu chí 4 — Story Consistency (10 điểm)**

PRD Day 17 có nhất quán với Day 16 Package không? Target User trong PRD có khớp với Customer Segment Card không? Problem Statement có gắn với Need Map không? Success Metrics có gắn với Value Proposition không?

---

**Tiêu chí 5 — Iteration Quality (20 điểm)**

Mức độ cải thiện thực sự giữa A và B. Thưởng người dám sửa core element (MVP scope, Fallback strategy, Hypothesis metric) sau khi nhận AI critique — không chỉ polish văn phong.

*Điểm Outstanding dành cho bài B vượt hẳn kỳ vọng so với A, kèm reflection honest về điều gì đã thay đổi và tại sao.*

---

### 6.3 Grade bands

| Band | Điểm | Ý nghĩa |
|---|---:|---|
| Outstanding | 90–100 | Output vượt template — PRD có insight riêng, Fallback UX thể hiện tư duy sản phẩm vượt guideline |
| Strong | 75–89 | Đủ chất để bắt đầu build, không cần revise mắt xích nào |
| Pass | 60–74 | Build được nhưng cần clarify ít nhất 1 phần trước khi giao cho engineer |
| Needs rework | 40–59 | PRD còn quá mơ hồ để build, cần làm lại AI-specific section hoặc Hypothesis |
| Fail | <40 | Chưa đạt minimum bar của Day 17 |

---

### 6.4 Lưu ý khi làm bài

- **Cụ thể hơn là đầy đủ.** Một Fallback UX mô tả rõ 1 scenario tốt hơn 3 scenario viết chung chung.
- **Mỗi thứ trong In-Scope phải map được về 1 Need cụ thể từ Day 16.** Nếu không map được — đó là scope creep.
- **Hypothesis phải sai được.** Nếu bạn không thể nghĩ ra cách Hypothesis này bị falsified — nó quá mơ hồ.
- **AI critique chỉ có ý nghĩa nếu bạn quyết định điều gì accept và điều gì reject.** Nộp bài mà không có reflection về AI feedback = chưa dùng AI đúng cách.

---

## 7. Final submission — Day 17 Package

Copy template dưới đây vào `submission.md` trong GitHub repo, điền đầy đủ.

```markdown
# Day 17 Submission
**Student:** [Tên]
**Date:** [Ngày]
**Product idea:** [1 câu mô tả ý tưởng]

---

## 1. MVP Boundary Sheet

**Riskiest Assumption:**
> [1 câu — giả định nguy hiểm nhất cần test]

**In-Scope** (tối đa 3):
- [ ] [Tính năng 1] — test giả định: [...]
- [ ] [Tính năng 2] — test giả định: [...]

**Out-of-Scope:**
- [Tính năng A] — lý do bỏ: [...]
- [Tính năng B] — lý do bỏ: [...]
- [Tính năng C] — lý do bỏ: [...]

**Non-Goals:**
- [Ranh giới đỏ 1]
- [Ranh giới đỏ 2]

---

## 2. PRD Skeleton

### Problem Statement
> [1 câu: Ai, đang gặp vấn đề gì, hậu quả kinh tế / vận hành là gì]

### Target User
> [Chân dung cụ thể — nối từ Customer Segment Card Day 16]

### User Stories
**Story 1:**
> As a [...], I want [...], so that [...]

**Story 2:**
> As a [...], I want [...], so that [...]

### AI-Specific

**Model Selection:**
- Model: [tên model]
- Lý do chọn: [giải thích]
- Trade-offs chấp nhận: [...]
- Trade-offs không chấp nhận: [...]

**Data Requirements:**
- Nguồn: [...]
- Owner: [...]
- Update frequency: [...]

**Fallback UX:**
- Chiến lược: [Expectation Management / Human-in-the-loop / Graceful Handover]
- Trigger: [Khi nào AI bị coi là không đủ tự tin?]
- Hành động: [Hệ thống làm gì cụ thể?]
- User options: [User có thể làm gì tiếp theo?]

### Success Metrics
- Primary metric: [...]
- Ngưỡng thành công: [...]
- Timeframe đo lường: [...]

### Dependencies & Constraints
- [...]

---

## 3. Hypothesis Table

### Hypothesis 1 (cho tính năng In-Scope #1)
> "Chúng tôi tin rằng [X] sẽ giúp [Y] đạt được [Z].
> Chúng tôi sẽ biết mình đúng khi thấy [metric] đạt [ngưỡng] trong [thời gian]."

Riskiest assumption: [...]
Cách test cheapest: [...]

### Hypothesis 2 (nếu có)
> [...]

---

## 4. PMF Scorecard

**Aha Moment:**
> [Mô tả hành vi cụ thể — không phải cảm giác]

**Actionable Metric:**
> [Tên metric + cách đo]

**PMF Method:**
> [Sean Ellis / Retention Curve / Aha Moment tracking]
> Ngưỡng thành công: [...]

**Vanity Metrics tôi sẽ không dùng:**
- [...]

---

## 5. AI Critique Log

**Điểm AI chỉ ra:**
1. [Issue 1] — Action: Accept / Reject / Partial — Lý do: [...]
2. [Issue 2] — Action: Accept / Reject / Partial — Lý do: [...]
3. [Issue 3] — Action: Accept / Reject / Partial — Lý do: [...]

**Thay đổi lớn nhất giữa Version A và Version B:**
> [Mô tả điều gì thay đổi và tại sao]

---

## 6. Self-assessment

Mắt xích nào trong [MVP Boundary → PRD → Hypothesis → PMF] bạn đang yếu nhất?
> [Trả lời thật]

Open questions bạn muốn giải đáp tiếp:
1. [...]
2. [...]
```

---

*Chúc các bạn build được sản phẩm thật — từ strategy, đến PRD, đến tay người dùng.*

---

## 8. References

### Core readings

1. **The Lean Product Playbook** — Dan Olsen
   [https://leanproductplaybook.com/](https://leanproductplaybook.com/)
   Framework gốc của Lean Product Pyramid. Chương 4–7 là phần liên quan trực tiếp nhất cho Day 17.

2. **How Superhuman Built an Engine to Find Product Market Fit** — Rahul Vohra
   [https://review.firstround.com/how-superhuman-built-an-engine-to-find-product-market-fit](https://review.firstround.com/how-superhuman-built-an-engine-to-find-product-market-fit)
   Bài viết gốc về PMF Engine và Sean Ellis Test được áp dụng vào thực tế.

3. **The Mom Test** — Rob Fitzpatrick
   Cách phỏng vấn user để validate hypothesis mà không bị "mom answer" làm lệch kết quả.

### Further reading (optional)

4. **Writing Good PRDs** — Jackie Bavaro & Gayle Laakmann McDowell *(Cracking the PM Interview)*
   Hướng dẫn viết PRD từ góc nhìn PM chuyên nghiệp.

5. **Measure What Matters** — John Doerr
   OKR framework — liên quan trực tiếp đến cách định nghĩa Success Metrics trong PRD.

6. **Inspired: How to Create Tech Products Customers Love** — Marty Cagan
   Tư duy product management chuyên sâu từ người từng làm VP Product tại eBay và HP.

7. **Shape Up** — Ryan Singer (Basecamp)
   [https://basecamp.com/shapeup](https://basecamp.com/shapeup)
   Phương pháp scope sản phẩm thực chiến — liên quan đến MVP Boundary và PRD Skeleton.

### Quick reference — các câu chốt Day 17

| Lúc nào nhớ câu nào |
|---|
| "MVP is the cheapest way to buy the truth from the market." |
| "The best MVP is the one that knows how to say NO." |
| "In traditional software, a button does what it's told. In AI, you must design for when it disobeys." |
| "The best Fallback UX is managing user expectations from second zero." |
| "PMF is not a feeling — it is an engineering process." |
| "Don't measure the busyness of the system, measure the behavior that creates core value." |
| "If a metric goes up but core behavior doesn't change — it's a vanity metric." |
| "A hypothesis must be falsifiable. If you can't imagine how it could be wrong — it's too vague." |

---

*Chúc các bạn build được sản phẩm thật — từ strategy, đến PRD, đến tay người dùng.*
