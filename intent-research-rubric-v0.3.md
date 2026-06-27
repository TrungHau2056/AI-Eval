# Rubric chấm Intent Research — v0.3

Dùng cho senior chấm deliverable Golden Persona Research của intern (phần 10 intent / domain). Gate INPUT trước khi intern bulk-write test case.

**Thay đổi vs v0.2**: 8 → 7 tiêu chí (bỏ Recovery Coverage độc lập + bỏ Stakes tag), gộp phase "Lỗi" thành mandatory trong Domain Coverage. Max điểm 52 → **44**.

---

## Định nghĩa Intent

**Intent = 1 việc user muốn làm khi nhắn AI.**

- Nhìn từ phía **user muốn gì**, không phải phía **hệ thống có gì**.
- 1 intent → nhiều **câu chat thật** khác nhau cùng map về.
- **Cấp độ**: đủ cụ thể để phân biệt user goal / info AI cần / success signal khác nhau; đủ chung để gộp parameter (model xe, ngày, địa điểm).

Test phân biệt + ví dụ áp dụng xem chi tiết tại **R1 Granularity** bên dưới.

---

## 7 Tiêu chí (sắp xếp theo weight)

| # | Tên EN | Tên VN | Weight |
|---|---|---|---|
| **R1** | **Granularity** | Cấp độ vừa | **3x** |
| **R2** | **Action Lens** | Tên intent là việc user muốn LÀM | 2x |
| **R3** | **Authentic Utterance** | Câu chat thật VN | 2x |
| **R4** | **Domain Coverage** | Cover đủ phase trong domain | 1x |
| **R5** | **Trigger Moment** | Context user gõ lúc nào | 1x |
| **R6** | **Evidence Sourcing** | Có nguồn (từ đâu ra) | 1x |
| **R7** | **Persona Attribution** | Gắn persona cho mỗi intent | 1x |

Tổng weight = 11 → Max điểm = **44**.

### Trần điểm tự động (Hard-fail caps)

| Trigger | Cap |
|---|---|
| R1 = 1 (granularity tệ) | 40% |
| R2 = 1 (toàn category) | 40% |
| R3 = 1 (không có utterance) | 50% |

### Ngưỡng kết luận

| Điểm | Verdict | Nghĩa |
|---|---|---|
| **≥75%** (33/44) | **Pass** | Greenlight intern bulk-write TC |
| **50–74%** | **Revision** | Fix gap rồi resubmit |
| **<50%** | **Rewrite** | Research lại từ đầu |

---

## Descriptor 4 mức per rubric

### R1 — Granularity (3x)

*Cấp độ vừa: không gộp 3 flow thành 1, không tách thành 1 keyword*

| Mức | Đặc điểm | Ví dụ intern viết |
|---|---|---|
| **1** | Quá rộng (gộp ≥3 flow) HOẶC quá hẹp (1 keyword/prompt cụ thể) | Rộng: "Mua xe" gộp đặt cọc + lái thử + so sánh. Hẹp: "Tìm trạm 22kW Hoàng Mai 7pm trời mưa" |
| **2** | Hơi lệch: gộp 2 flow HOẶC tách parameter thành intent riêng | "Hỏi giá xe" gộp lăn bánh + trả góp. HOẶC "Đặt lịch VF8" + "Đặt lịch VF9" = 2 intent |
| **3** | Vừa, 1-2 intent chưa parameter hoá rõ | Đa số đúng cấp, vài chỗ lặp parameter |
| **4** | Đúng cấp + parameter hoá + pass test 3-câu | "Đặt lịch lái thử" (model+ngày=parameter), khác "Đổi lịch" (goal khác), khác "Huỷ lịch" (success signal khác) |

**Cách chấm**:
1. Scan 10 intent — phát hiện cái nào quá rộng (category umbrella như "Mua xe") hay quá hẹp (1 keyword như "Trạm 22kW Hoàng Mai 7pm").
2. Với mỗi cặp 2 intent gần nhau (vd "Hỏi giá" vs "Hỏi trả góp"), áp test 3-câu **user-observable** (không cần touch hệ thống):
   - User muốn đạt được gì? (goal)
   - AI cần biết gì để giúp? (info user phải cung cấp)
   - User biết thành công như nào? (success signal)

   Cả 3 cùng = phải gộp; khác ≥1 = đúng tách.
3. Đếm số cặp đúng tách/gộp + check 10 intent có ở đúng cấp không.
4. Pick mức: rộng/hẹp xuyên list→1 / lệch 2-3 chỗ→2 / vừa, 1-2 chỗ lặp parameter→3 / đúng cấp + pass test mọi cặp→4.

Thời gian ước lượng: **5-7 phút**.

**Ví dụ minh hoạ**:

Case A — "Hỏi giá lăn bánh" vs "Hỏi giá trả góp" (intern viết tách 2 intent):

| Câu hỏi | Lăn bánh | Trả góp | Khác? |
|---|---|---|---|
| Goal | Biết tổng phí mua xe | Biết tháng trả bao nhiêu | Khác |
| Info AI cần | Model + tỉnh đăng ký | Model + DP + kỳ hạn | Khác |
| Success signal | Con số one-time | Con số monthly | Khác |

→ Cả 3 khác → đúng tách. R1 OK chỗ này.

Case B — "Lái thử VF8" vs "Lái thử VF9" (intern viết tách 2 intent):

| Câu hỏi | VF8 | VF9 | Khác? |
|---|---|---|---|
| Goal | Trải nghiệm xe | Trải nghiệm xe | Cùng |
| Info AI cần | Showroom + ngày | Showroom + ngày | Cùng |
| Success signal | Lái thử được model | Lái thử được model | Cùng |

→ Cả 3 cùng → nên gộp "Lái thử" (model = parameter). Tách = sai, R1 trừ điểm.

---

### R2 — Action Lens (2x)

*Tên intent phải là việc user muốn LÀM (verb+object), không phải tên feature/category*

| Mức | Đặc điểm | Ví dụ intern viết |
|---|---|---|
| **1** | Toàn category nội bộ / tên module | "Vận tải" / "Bảo hành" / "Hỗ trợ" / "Khiếu nại" / "Thông tin" |
| **2** | Vài action, đa số category | "Lái thử" / "Sạc xe" / "Tư vấn" — action ngầm trong noun |
| **3** | Đa số action, vài chỗ generic verb "hỏi"/"xem" | "Đặt lịch lái thử" / "Hỏi giá" / "Xem thông tin xe" |
| **4** | Toàn verb cụ thể + object concrete | "Đặt lịch lái thử VF8" / "Tìm trạm sạc gần" / "So sánh VF8 vs Tesla Y" |

**Cách chấm**:
1. Đọc 10 tên intent.
2. Đếm bao nhiêu cái là **verb cụ thể + object concrete** (vd "Đặt lịch lái thử VF8" ✓; "Vận tải" ✗ vì noun category; "Hỏi" ✗ vì verb generic).
3. Pick mức: 0-2 cụ thể→1 / 3-5→2 / 6-8→3 / 9-10→4.

Thời gian ước lượng: **1 phút**.

**Ví dụ minh hoạ**:

| List intern nộp | Đếm | Mức |
|---|---|---|
| "Vận tải / Sạc xe / Mua xe / Bảo hành / Tư vấn / Thanh toán / Đăng ký / Hỗ trợ / Khiếu nại / Thông tin" | 0/10 verb cụ thể (toàn category) | 1 |
| "Đặt lịch lái thử / Đổi lịch / Tìm trạm sạc / Hỏi giá / Hỏi spec / Đặt cọc / Hỏi trả góp / Hỏi bảo hành / So sánh xe / Hỏi thời gian giao" | 7/10 action ("Đặt", "Đổi", "Tìm", "Đặt cọc", "So sánh"), 3 generic "Hỏi" | 3 |
| "Đặt lịch lái thử VF8 tại showroom gần / Tìm trạm sạc gần / Báo trạm sạc hỏng / Đặt cọc VF8 online / So sánh VF8 vs Tesla Y / Hỏi khuyến mãi đang chạy / Báo hết pin / Lộ trình road-trip / Tra cứu lịch sử sạc / Sạc tại chung cư" | 10/10 verb cụ thể + object concrete | 4 |

---

### R3 — Authentic Utterance (2x)

*Mỗi intent kèm câu user gõ thật (cụt, lowercase, abbr, particle) — không formal sách giáo khoa*

| Mức | Đặc điểm | Ví dụ utterance kèm intent "Đặt lịch lái thử" |
|---|---|---|
| **1** | Không có utterance, hoặc utterance = lặp tên intent | (trống) hoặc "Đặt lịch lái thử" |
| **2** | Formal sách giáo khoa — chủ ngữ đầy, từ trang trọng | "Tôi muốn đặt lịch lái thử xe VinFast VF8 vào cuối tuần" |
| **3** | Natural nhưng hơi formal — bớt chủ ngữ chưa cụt | "đặt lịch lái thử vf8 thứ 7 nhé" |
| **4** | VN reality — cụt, lowercase, abbr, particle, code-switch | "đặt lái thử vf8 t7 ở long biên đc k" |

**Đặc điểm VN reality**: cụt (bỏ chủ ngữ), lowercase, viết tắt (k = không, đc = được, t7 = thứ 7, cn = chủ nhật), particle (nhé, đi, với), code-switch (test drive, DC fast).

**Cách chấm**:
1. Đọc utterance kèm mỗi intent.
2. Check 5 đặc điểm VN reality cho từng câu: cụt? lowercase? viết tắt? particle? code-switch?
3. Pick mức: không có hoặc lặp tên intent→1 / formal sách giáo khoa→2 / natural hơi formal→3 / VN reality đủ 4-5 đặc điểm→4.

Thời gian ước lượng: **2 phút**.

**Ví dụ minh hoạ**:

Cùng intent "Đặt lịch lái thử VF8":

| Utterance intern viết | Đặc điểm | Mức |
|---|---|---|
| (trống) hoặc "Đặt lịch lái thử" | Không có / lặp tên intent | 1 |
| "Tôi muốn đặt lịch lái thử xe VinFast VF8 vào cuối tuần này" | Chủ ngữ đầy + uppercase + trang trọng | 2 |
| "đặt lịch lái thử vf8 thứ 7 nhé" | Bỏ chủ ngữ ✓ lowercase ✓ particle "nhé" ✓; nhưng "thứ 7" chưa abbr | 3 |
| "đặt lái thử vf8 t7 ở long biên đc k" | Cụt ✓ lowercase ✓ abbr (t7, đc) ✓ particle "k" ✓ | 4 |

---

### R4 — Domain Coverage (1x)

*10 intent span đủ phase trong domain, không cluster 1 góc, có phase "Lỗi"*

| Mức | Cover được | Ví dụ list 10 intent Sạc xe |
|---|---|---|
| **1** | 1 phase (cluster 1 góc) | Toàn "Tìm trạm" (chỉ phase Khám phá) |
| **2** | 2 phase | Tìm trạm + Hỏi giá (Khám phá + Thanh toán) |
| **3** | 3–4 phase | + Báo trạm hỏng + Tra cứu lịch sử |
| **4** | **≥5 phase + có phase "Lỗi" + không phase nào >40% intent** | Đủ Khám phá / Đặt trước / Đang sạc / Sau sạc / Thanh toán / **Lỗi** |

**Phase mỗi domain tự define**. Ví dụ:

| Domain | 6 phase mẫu |
|---|---|
| Sạc xe điện | Khám phá / Đặt trước / Đang sạc / Sau sạc / Thanh toán / **Lỗi** |
| Lái thử ô tô | Khám phá / Đặt lịch / Trước hẹn / Tại showroom / Sau hẹn / **Lỗi** (huỷ/báo muộn) |
| Đặt phòng Vinpearl | Khám phá / So giá / Đặt phòng / Trước check-in / Trong kỳ nghỉ / **Lỗi** (huỷ/đổi/complain) |
| Tra cứu lịch khám | Tìm BS/khoa / Đặt lịch / Trước hẹn / Tại phòng khám / Sau khám / Tái khám + **Lỗi** |

**Quy tắc đặc biệt**:
- Phase "Lỗi" **bắt buộc có ở mức 4** — đây là cách rubric vẫn check recovery.
- Không phase nào chiếm >40% intent. Vd 5/10 intent đều "tìm trạm" → cluster, dù cover 4 phase khác vẫn fail mức 4.

**Cách chấm**:
1. Đọc cột Phase intern tự tag cho mỗi intent (nếu intern không tag, senior tự suy dựa trên tên intent + moment).
2. Đếm số phase distinct được cover (vd "Khám phá / Đặt trước / Lỗi" = 3 phase).
3. Check: phase "Lỗi" có mặt không?
4. Check: không phase nào chiếm >40% intent (vd 5/10 đều cùng phase = cluster).
5. Pick mức: 1 phase→1 / 2 phase→2 / 3-4 phase→3 / ≥5 phase + có Lỗi + không cluster→4.

Thời gian ước lượng: **3 phút**.

**Ví dụ minh hoạ**:

Domain "Sạc xe điện" — 6 phase: Khám phá / Đặt trước / Đang sạc / Sau sạc / Thanh toán / Lỗi.

Case A — Intern liệt kê 10 intent đều về "tìm trạm" (tìm gần, tìm dọc đường, tìm nhanh, tìm Vingroup, tìm tại Hà Nội, tìm DC fast, ...): tất cả thuộc phase Khám phá → **mức 1**.

Case B — Intern liệt kê 10 intent, tag phase:

| Intent | Phase |
|---|---|
| Tìm trạm gần / Lộ trình road-trip / So sánh DC vs AC | Khám phá (3) |
| Đặt slot trước | Đặt trước (1) |
| Sạc tại nhà chung cư | Đang sạc (1) |
| Tra cứu lịch sử sạc | Sau sạc (1) |
| Hỏi giá / Khuyến mãi | Thanh toán (2) |
| Báo trạm hỏng / Hết pin giữa đường | Lỗi (2) |

→ 6 phase ✓ + có Lỗi ✓ + Khám phá 3/10 = 30% < 40% ✓ → **mức 4**.

---

### R5 — Trigger Moment (1x)

*Mỗi intent attach context "user gõ câu này lúc nào, đang ở đâu, đang lo gì"*

| Mức | Đặc điểm | Ví dụ moment attach vào intent "Tìm trạm sạc" |
|---|---|---|
| **1** | Không context — chỉ tên action | "Tìm trạm sạc gần" |
| **2** | Hint generic | "Tìm trạm sạc khi cần sạc" / "khi đi xa" |
| **3** | Có context nhưng vẫn chung chung | "Tìm trạm sạc khi đang đi đường dài cuối tuần" |
| **4** | Concrete: **where + what doing + what worried** | "Tìm trạm sạc khi pin <20% và đang ở trạm dừng cao tốc" / "Báo hết pin giữa ca Xanh SM lúc 10pm gần Mỹ Đình" |

**Cách chấm**:
1. Đọc cột Moment intern viết cho mỗi intent.
2. Check 3 yếu tố concrete: **where** (chỗ nào)? **what doing** (đang làm gì)? **what worried** (đang lo gì)?
3. Pick mức: trống / lặp tên→1 / hint generic ("khi cần")→2 / có context nhưng vẫn chung chung→3 / concrete đủ 3 yếu tố→4.

Thời gian ước lượng: **1 phút**.

**Ví dụ minh hoạ**:

Cùng intent "Tìm trạm sạc":

| Moment intern viết | Where | What doing | What worried | Mức |
|---|---|---|---|---|
| (trống) | — | — | — | 1 |
| "Khi cần sạc" | — | — | — | 2 |
| "Khi đang đi đường dài cuối tuần" | đường dài (chung) | đi cuối tuần | — | 3 |
| "Đang chạy ca Xanh SM lúc 22h, pin còn 15% gần Mỹ Đình, lo không kịp về điểm sạc base" | gần Mỹ Đình ✓ | đang chạy ca XSM 22h ✓ | không kịp về base ✓ | 4 |

---

### R6 — Evidence Sourcing (1x)

*Mỗi intent kèm nguồn (interview ai / observation đâu / forum / ticket)*

| Mức | Đặc điểm | Ví dụ source intern kèm |
|---|---|---|
| **1** | 0/10 intent có source — brainstorm tại bàn | (trống) |
| **2** | <50% có source | "Theo PRD" / "Đoán" cho đa số |
| **3** | ≥50% có source, 1 loại duy nhất | Toàn "Interview user 1, 2, 3" — không có observation/ticket/forum |
| **4** | ≥80% có source + ≥2 loại nguồn khác nhau | Interview Xanh SM driver + Forum F88 EV + Support ticket + Observation tại trạm Cát Linh |

**Cách chấm**:
1. Đếm số intent có source note rõ (vd "Interview P3 ngày 2026-05-15" — KHÔNG accept "đoán" / "theo PRD").
2. Đếm số **loại** nguồn khác nhau: interview / observation / forum / ticket / chat log.
3. Pick mức: 0/10→1 / <50% có→2 / ≥50% nhưng 1 loại duy nhất→3 / ≥80% có + ≥2 loại→4.

Thời gian ước lượng: **1 phút**.

**Ví dụ minh hoạ**:

| Cột Source của 10 intent | Đánh giá | Mức |
|---|---|---|
| 10 ô trống | 0/10 có source — brainstorm tại bàn | 1 |
| 4/10 ghi "Theo PRD VinFast" + 6/10 trống | <50% có + "PRD" không phải research thật | 2 |
| 7/10 ghi "Interview Xanh SM driver A/B/C/D" + 3/10 trống | ≥50% có nhưng 1 loại duy nhất (interview) | 3 |
| 9/10 có — 4 interview driver + 2 thread forum F88 + 2 ticket support + 1 observation tại trạm Cát Linh | ≥80% có + 4 loại nguồn | 4 |

---

### R7 — Persona Attribution (1x)

*Mỗi intent gắn 1 persona primary trong 4 persona đã chốt*

| Mức | Đặc điểm | Ví dụ |
|---|---|---|
| **1** | 0/10 intent gắn persona | Intent generic, không biết phục vụ ai |
| **2** | <50% gắn persona | 3/10 gắn, 7/10 chung chung |
| **3** | ≥50% gắn, nhưng tập trung 1-2 persona | 8/10 gắn P3 Xanh SM, miss P1/P2/P4 |
| **4** | ≥80% gắn + spread đều 4 persona | 9/10 gắn, có ≥1 intent cho mỗi P1/P2/P3/P4 |

**Lưu ý**: 1 intent có thể gắn ≥1 persona (vd "Báo trạm hỏng" gắn cả P1 chung cư + P3 Xanh SM). Tag primary persona quan trọng nhất.

**Cách chấm**:
1. Đếm số intent gắn persona (trong 4 persona đã chốt — P1/P2/P3/P4).
2. Check spread: mỗi persona P1, P2, P3, P4 đều có ít nhất 1 intent không?
3. Pick mức: 0 gắn→1 / <50% gắn→2 / ≥50% gắn nhưng cluster 1-2 persona→3 / ≥80% gắn + spread đều 4 persona→4.

Thời gian ước lượng: **1 phút**.

**Ví dụ minh hoạ**:

4 persona Pin & Sạc đã chốt: P1 chung cư / P2 family road-trip / P3 Xanh SM / P4 anxiety new EV.

| Cột Persona của 10 intent | Phân tích | Mức |
|---|---|---|
| 0/10 gắn | Generic, không biết phục vụ ai | 1 |
| 4/10 gắn — đều P3 | <50% + chỉ 1 persona | 2 |
| 8/10 gắn — 6 P3 + 2 P1 | ≥50% nhưng cluster P3, miss P2/P4 | 3 |
| 9/10 gắn — 3 P1 + 2 P2 + 3 P3 + 2 P4 (có overlap) | ≥80% + spread đều 4 persona | 4 |

---

## Workflow chấm tổng quan — 30 phút / 1 deliverable

| Bước | Thời gian | Việc |
|---|---|---|
| 1 | 5p | Đọc nhanh 10 intent + utterance + moment + source + persona + phase tag |
| 2 | 15p | Chấm 7 rubric theo thứ tự R1→R7 (mỗi cái xem "Cách chấm" trong section tương ứng) |
| 3 | 2p | Tính tổng × weight + check 3 trần điểm |
| 4 | 8p | Viết verdict + top 3 fix |

### Template intern bắt buộc nộp — 7 cột

| Cột | Bắt buộc | Ví dụ |
|---|---|---|
| Intent | ✓ | Đặt lịch lái thử VF8 |
| Utterance (≥1) | ✓ | "đặt lái thử vf8 t7 ở long biên đc k" |
| Moment | ✓ | User đã xem brochure online, muốn cảm nhận xe thật trước khi quyết mua |
| Source | ✓ | Interview P4 (anxiety) — record 2026-05-15 |
| Persona | ✓ | P4 |
| Phase | ✓ | Đặt lịch |

Cột thiếu = tự động trừ điểm rubric tương ứng (vd thiếu cột Phase → R4 không chấm được, default mức 1).

### Tính tổng

```
Tổng = R1×3 + R2×2 + R3×2 + R4×1 + R5×1 + R6×1 + R7×1
% = Tổng / 44

Check trần điểm (theo thứ tự):
- R1 = 1 → cap % = min(%, 40%)
- R2 = 1 → cap % = min(%, 40%)
- R3 = 1 → cap % = min(%, 50%)

Verdict:
- ≥75% → Pass (greenlight bulk-write TC)
- 50-74% → Revision (fix + resubmit)
- <50% → Rewrite
```

### Top 3 fix — template feedback

Viết 3 dòng, mỗi dòng theo format:
- **Rubric X (điểm hiện tại / 4)** — gap cụ thể — action concrete intern phải làm

Ví dụ:
- **R3 Authentic Utterance (2/4)** — utterance đang formal sách giáo khoa ("Tôi muốn đặt lịch lái thử xe VinFast VF8") — đổi sang VN reality kiểu "đặt lái thử vf8 t7 đc k", check 5 đặc điểm cụt/lowercase/abbr/particle/code-switch
- **R4 Domain Coverage (3/4)** — miss phase "Lỗi" — thêm 2 intent recovery cụ thể: "Huỷ lịch lái thử" + "Báo xe lái thử muộn"
- **R6 Evidence Sourcing (2/4)** — 6/10 intent không có source — interview thêm 2 user thật + đọc 1 thread forum F88 để có 2 loại nguồn

---

## 3 ví dụ chấm thử

### Ví dụ A — Intern lười (toàn category, không utterance, không source)

**10 intent**: Vận tải / Sạc xe / Mua xe / Bảo hành / Tư vấn / Thanh toán / Đăng ký / Hỗ trợ / Khiếu nại / Thông tin
**Utterance kèm**: Không có
**Source kèm**: Không có
**Persona kèm**: Không có

| # | Rubric | W | Raw | × |
|---|---|---|---|---|
| R1 | Granularity | 3 | 1 | 3 |
| R2 | Action Lens | 2 | 1 | 2 |
| R3 | Authentic Utterance | 2 | 1 | 2 |
| R4 | Domain Coverage | 1 | 2 | 2 |
| R5 | Trigger Moment | 1 | 1 | 1 |
| R6 | Evidence Sourcing | 1 | 1 | 1 |
| R7 | Persona Attribution | 1 | 1 | 1 |
| | **Tổng** | | | **12/44 = 27%** |

→ **Rewrite**. Hard-fail cap 40% (R1=1, R2=1) + cap 50% (R3=1) — không bind vì đã 27%.

**Top 3 fix**:
1. Chuyển category → user action ("Vận tải" → "Tìm xe đi từ A đến B")
2. Mỗi intent kèm câu user gõ thật VN reality
3. Tách "Hỗ trợ" / "Khiếu nại" thành intent cụ thể trong phase "Lỗi"

---

### Ví dụ B — Intern khá (action OK, formal utterance, source yếu)

**10 intent**: Đặt lịch lái thử / Đổi lịch / Tìm trạm sạc gần / Hỏi giá / Hỏi spec / Đặt cọc / Hỏi trả góp / Hỏi bảo hành / So sánh xe / Hỏi thời gian giao
**Utterance kèm**: "Tôi muốn đặt lịch lái thử xe VF8" / "Cho tôi xem giá xe VF9"
**Source kèm**: 4/10 có "interview user X"
**Persona kèm**: 4/10 gắn P2 (gia đình mua xe đầu)

| # | Rubric | W | Raw | × |
|---|---|---|---|---|
| R1 | Granularity | 3 | 3 | 9 |
| R2 | Action Lens | 2 | 3 | 6 |
| R3 | Authentic Utterance | 2 | 2 | 4 |
| R4 | Domain Coverage | 1 | 3 (3-4 phase: Khám phá + Đặt lịch + Thanh toán + Lỗi nhẹ qua "Đổi lịch") | 3 |
| R5 | Trigger Moment | 1 | 2 | 2 |
| R6 | Evidence Sourcing | 1 | 2 | 2 |
| R7 | Persona Attribution | 1 | 2 | 2 |
| | **Tổng** | | | **28/44 = 64%** |

→ **Revision required**.

**Top 3 fix**:
1. Đổi utterance sang VN reality: "đặt lái thử vf8 t7 ở long biên đc k"
2. Add intent recovery cụ thể: "Huỷ lịch lái thử" + "Báo xe lái thử muộn" + "Không thấy lịch của tôi" → đẩy R4 lên 4
3. Add source cho 6/10 intent còn thiếu + gắn persona cho 6/10

---

### Ví dụ C — Intern tốt (action concrete + utterance VN + phase đủ + persona spread)

**10 intent**: Đặt lịch lái thử VF8 tại showroom gần / **Đổi-huỷ lịch lái thử** / Tìm trạm sạc gần chỗ đang đứng / Lộ trình + chiến lược sạc road-trip Hà Nội-Đà Nẵng / Báo trạm sạc bị chiếm hoặc hỏng / Đặt cọc VF8 online / Hỏi khuyến mãi đang chạy / Báo hết pin giữa ca Xanh SM / So sánh VF8 vs Tesla Model Y / Sạc tại nhà chung cư có ổ chung

**Utterance kèm**: "đặt lái thử vf8 t7 ở long biên đc k" / "đg chạy xanh sm hết pin gần mỹ đình" / "trạm cát linh chiếm chỗ mà k sạc"
**Source kèm**: 8/10 có source — 4 interview Xanh SM driver, 2 forum F88, 2 ticket support
**Persona kèm**: 9/10 gắn — spread P1 (chung cư) / P2 (road-trip) / P3 (Xanh SM) / P4 (anxiety new EV)

| # | Rubric | W | Raw | × |
|---|---|---|---|---|
| R1 | Granularity | 3 | 3 (gộp "đổi-huỷ" 1 intent = miss tách recovery khác) | 9 |
| R2 | Action Lens | 2 | 4 | 8 |
| R3 | Authentic Utterance | 2 | 4 | 8 |
| R4 | Domain Coverage | 1 | 4 (cover ≥5 phase + có phase Lỗi) | 4 |
| R5 | Trigger Moment | 1 | 4 | 4 |
| R6 | Evidence Sourcing | 1 | 3 | 3 |
| R7 | Persona Attribution | 1 | 3 | 3 |
| | **Tổng** | | | **39/44 = 89%** |

→ **Pass**. Greenlight bulk-write TC.

**Note cải thiện** (không blocking):
- R1: tách "Đổi lịch" và "Huỷ lịch" thành 2 intent (recovery khác nhau → R1 lên 4)
- R6: thêm observation tại trạm + ticket support → 3 loại nguồn (R6 lên 4)
- R7: gắn persona cho 1 intent còn thiếu (R7 lên 4)

---

## Failure mode hệ thống — cần training riêng

Quan sát xuyên 3 ví dụ — 3 dimension intern thường yếu:

1. **R3 Authentic Utterance**: A/B ≤2 → training VN typing reality (ref `vn_typing_reality`)
2. **R6 Evidence Sourcing**: cả 3 ≤3 → checklist "≥80% intent kèm source, ≥2 loại nguồn"
3. **R7 Persona Attribution**: cả 3 ≤3 → buộc intern map từng intent về 1 trong 4 persona đã chốt

---

## Calibration

- 2 senior chấm độc lập trên cùng 1 deliverable.
- Tính IAA (Inter-Annotator Agreement): chấp nhận khi Cohen's κ ≥ 0.7.
- Disagree ≥2 điểm trên 1 tiêu chí → debate + cập nhật descriptor.
- Round 1 nếu κ < 0.7 thường do mức 3 cover quá rộng → v0.4 cân nhắc tách mức 3 thành 3a (chạm sàn) + 3b (khá).

---

## Version

v0.3 — 2026-06-01 — tinh giản tiếp từ v0.2 sau 2 vòng audit (MECE / self-framework / adversarial) + 5 constraint clarify từ user:

1. Intern làm research dựa trên domain, không từ PRD → drop Surprise (v0.2).
2. Intern không access log/data → drop Frequency tier (v0.2).
3. Intern cover domain rộng, không sản phẩm độc lập có scope cứng → drop Boundary (v0.2).
4. Recovery là khái niệm luồng sản phẩm, không domain → **drop Recovery Coverage độc lập, gộp phase "Lỗi" thành mandatory trong Domain Coverage** (v0.3).
5. Stakes (low/mid/high) không universal across domain — domain low-stakes (lái thử/tư vấn) sẽ ép bịa → **drop Stakes tag, giữ Trigger Moment concrete context** (v0.3).
6. Test 3-câu cũ (code path / UX / recovery) yêu cầu access hệ thống AI → intern/senior non-tech không operational → **reframe sang user-observable (goal / info AI cần / success signal)**, chỉ cần quan sát + phỏng vấn user (v0.3).

Sắp xếp theo weight: R1 Granularity (3x) là foundation duy nhất; R2 Action Lens + R3 Authentic Utterance (2x mỗi cái) là user-reality proof; R4-R7 (1x mỗi cái) là context/breadth/source/persona layer.
