# Product Requirements Document (PRD)
**Product Name:** AI Test Case Generator (MVP)
**Document Status:** Draft
**Target Platform:** Web App (Streamlit)

---

## 1. Problem Statement
Hiện tại, quá trình xây dựng bộ Test Case để đánh giá AI/Chatbot đang được thực hiện hoàn toàn thủ công. Đội ngũ Researcher phải tự đọc hàng nghìn phản hồi, comment thô của user để tự gom cụm nhóm Intent, tự suy luận ra Persona, và tự nghĩ ra các Prompt đóng vai.
Vấn đề này dẫn đến:
*   Tốn quá nhiều thời gian (nhiều ngày/tuần) để làm xong một bộ test case chất lượng.
*   Dễ mang định kiến cá nhân (bias) của người làm test, dẫn đến test case không phản ánh đúng 100% ngữ cảnh thực tế của user.
*   Khó mở rộng (scale) khi sản phẩm liên tục có thêm tính năng và luồng dữ liệu mới.

## 2. Target User
*   **AI Product Researcher / Prompt Engineer / QA:** Những người chịu trách nhiệm nghiên cứu hành vi người dùng, đánh giá chất lượng phản hồi của LLM, và tinh chỉnh các luồng tương tác của hệ thống.

## 3. User Stories
*   **US1 (Nhập liệu):** Là một Researcher, tôi muốn dán trực tiếp đoạn văn bản thô hoặc tải lên file CSV chứa phản hồi của người dùng để tôi có thể nhanh chóng nạp dữ liệu vào hệ thống mà không cần viết code thu thập (crawler) hay xử lý dữ liệu phức tạp.
*   **US2 (Khai phá Intent):** Là một Researcher, tôi muốn hệ thống tự động phân tích văn bản đầu vào và liệt kê tất cả các Intent (Bối cảnh -> Mục tiêu) tiềm năng để tôi không phải tự đọc và gom nhóm hàng trăm comment bằng tay.
*   **US3 (Tạo Persona):** Là một Researcher, tôi muốn hệ thống sinh ra 2 Persona trái ngược nhau cho mỗi Intent đã duyệt để các test case của tôi bao phủ được cả những kịch bản người dùng dễ và khó.
*   **US4 (Human-in-the-loop):** Là một Researcher, tôi muốn xem lại, chỉnh sửa hoặc xóa các Intent và Persona do AI tạo ra trước khi chuyển sang bước sinh Prompt để tôi có thể kiểm soát chất lượng đầu ra và ngăn chặn việc AI bị ảo giác.
*   **US5 (Xuất dữ liệu):** Là một Researcher, tôi muốn tải xuống các test prompt cuối cùng dưới dạng file CSV/Markdown để tôi có thể dễ dàng đưa chúng vào không gian làm việc đánh giá thủ công hiện tại của mình.

## 4. MVP Scope (Ranh giới MVP)
| Khái niệm | Chi tiết |
|---|---|
| **In-Scope** | - Giao diện upload file CSV hoặc paste text (Streamlit).<br>- Chuỗi 3 Prompt LLM (Khai phá Intent -> Tạo Persona -> Viết Test Prompt).<br>- Tính năng cho phép User edit kết quả sau mỗi bước.<br>- Nút Export file `.csv` và `.md`. |
| **Out-of-Scope** | - Tự động crawl dữ liệu từ các trang mạng xã hội/web.<br>- Lưu trữ database, quản lý lịch sử versioning.<br>- Chấm điểm tự động (LLM-as-a-judge). |
| **Non-Goals** | - Thay thế hoàn toàn tư duy đánh giá của Researcher. Tool này đóng vai trò trợ lý sinh ý tưởng, không tự động hóa 100% việc ra quyết định. |

## 5. Success Metrics
*   **Time-to-value:** Giảm 80% thời gian từ lúc có data thô đến lúc ra được bộ Test Case chuẩn (VD: Từ 3 ngày xuống còn 2 giờ).
*   **Adoption Rate:** Tỷ lệ % các Intent / Persona / Prompt do AI sinh ra được Researcher giữ nguyên hoặc chỉ chỉnh sửa nhỏ (<20% text) trước khi bấm Export.

## 6. Dependencies & Constraints
*   **Dependencies:** Cần có API Key của một mô hình LLM đủ thông minh (Gemini 1.5 Pro hoặc GPT-4o) để xử lý logic suy luận. Thư viện Streamlit để dựng UI.
*   **Constraints:** Giới hạn Context Window của LLM (nếu người dùng paste cục text quá dài, cần có logic chia nhỏ - chunking). Nguy cơ chạm limit API rate khi sinh hàng loạt test case cùng lúc.

---

## Các thành phần bắt buộc cho AI PRD

## 7. Model Selection Rationale
**Lựa chọn:** `Gemini 1.5 Pro` hoặc `GPT-4o`.
**Lý do:**
*   **Accuracy vs Cost:** Việc "Khai phá Intent" và "Tạo Persona đối lập" đòi hỏi khả năng suy luận logic sâu và hiểu sắc thái tâm lý con người rất cao. Các model nhỏ (để tiết kiệm chi phí) sẽ dễ sinh ra các persona ngô nghê, rập khuôn.
*   **Context Window:** Gemini 1.5 Pro (với 1M-2M tokens) là lựa chọn cực kỳ lý tưởng vì researcher có thể paste nguyên một file transcript phỏng vấn rất dài vào mà không bị rớt ngữ cảnh.
*   **Latency:** Đây là tool dùng nội bộ cho quy trình Research, không phải real-time API cho end-user, nên độ trễ (latency vài chục giây cho mỗi lượt sinh) là hoàn toàn chấp nhận được.

## 8. Data Requirements
*   **Nguồn dữ liệu:** Do người dùng (Researcher) tự tải lên dưới dạng file tĩnh (CSV) hoặc paste text trực tiếp.
*   **Quyền sở hữu:** Dữ liệu hoàn toàn thuộc về phía người dùng, công cụ không lưu trữ lại dữ liệu vào database trên máy chủ.
*   **Freshness:** Dữ liệu tĩnh tại thời điểm chạy. Không yêu cầu real-time update.
*   **Quality control:** Bắt buộc phía Researcher phải dọn dẹp các thông tin cá nhân nhạy cảm (PII - Personally Identifiable Information) trước khi paste vào tool để đảm bảo Privacy.

## 9. Fallback UX
**Chiến lược cốt lõi: Human-in-the-loop (Con người can thiệp giữa các vòng lặp)**

Trong hệ thống AI tạo sinh nội dung, rủi ro lớn nhất là AI "ảo giác" hoặc suy luận sai ngữ cảnh thực tế của sản phẩm. Vì vậy, ứng dụng sẽ không chạy tuột một mạch từ Input ra Output.

*   **Thiết kế UX:** 
    1. Chạy AI Bước 1 (Sinh Intent) -> **TẠM DỪNG**. Hiển thị kết quả ra một bảng (Data Grid).
    2. User có thể bấm vào từng ô để sửa tên Intent, xóa Intent rác, hoặc thêm Intent mới.
    3. User bấm nút "Chốt Intent -> Chạy tiếp Bước 2".
    4. Tương tự cho bước tạo Persona và sinh Test Prompt.
*   **Graceful Handover (Tái tạo kết quả):** Nếu AI sinh ra bộ Persona quá chung chung, cung cấp một nút "Regenerate" kèm theo một ô nhập liệu nhỏ: *"Hướng dẫn thêm cho AI (VD: Hãy làm Persona A khó tính hơn)"*. Nếu AI vẫn làm tệ, user hoàn toàn có thể tự gõ đè kết quả của mình vào ô text để đi tiếp.
