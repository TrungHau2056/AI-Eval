// Mock guideline content (Vietnamese markdown) shown in collapsible GuidelinePanel
// above each "gen" button. User có thể Edit/Reset — bản chỉnh sửa lưu trong localStorage.

export const GUIDELINE_KEYS = {
  intent: 'ai_eval_guideline_intent',
  subintent: 'ai_eval_guideline_subintent',
  persona: 'ai_eval_guideline_persona',
  singleTurn: 'ai_eval_guideline_single_turn',
} as const;

export const INTENT_GUIDELINE = `# Guideline tạo Intent

Intent là **mục đích thực sự** của người dùng đằng sau một câu nói / hành động.
Mục tiêu của bước này: từ raw data, trích xuất ra các intent rõ ràng, không trùng lặp.

## Nguyên tắc
- Mỗi intent gồm **Context** (bối cảnh) và **Goal** (mục tiêu) tách bạch, không lặp ý.
- Goal phải cụ thể, đo lường được — tránh chung chung kiểu "muốn được hỗ trợ".
- Ưu tiên intent có *evidence* (dẫn chứng) thực tế từ raw data.
- Gộp các câu nói cùng mục đích thành **một** intent; tách nếu mục đích khác nhau.

## Ví dụ
| Context | Goal |
|---|---|
| User đang xem lại lộ trình học | Tìm cách đặt lịch học theo nhóm |
| User gặp lỗi khi làm bài kiểm tra | Báo lỗi và tiếp tục được bài thi |

> Chỉnh guideline này để định hướng AI bám sát domain của bạn trước khi bấm "Chạy Intent Discovery".
`;

export const SUBINTENT_GUIDELINE = `# Guideline tạo Sub-Intent

Sub-Intent là các **ý định con** chi tiết hoá một Intent cha thành những tình huống cụ thể
hơn để sinh test case sát thực tế.

## Nguyên tắc
- Mỗi Intent cha nên có **2–4 sub-intent** bao phủ các biến thể khác nhau.
- Sub-intent phải **không chồng lấn** nhau và đều thuộc phạm vi của Intent cha.
- Đặt **Title** ngắn gọn + **Description** mô tả tình huống/điều kiện cụ thể.
- Ưu tiên phủ các trường hợp biên (happy path, lỗi, thiếu thông tin...).

## Ví dụ (Intent: "Đặt lịch học theo nhóm")
- **Tạo nhóm mới** — user chưa có nhóm, cần tạo và mời thành viên.
- **Đổi lịch nhóm** — nhóm đã có, cần dời buổi học sang khung giờ khác.
- **Xung đột lịch** — thành viên báo trùng lịch, cần xử lý.

> Chỉnh guideline này trước khi bấm "Gen Sub-Intent".
`;

export const PERSONA_GUIDELINE = `# Guideline tạo Persona

Persona mô phỏng **kiểu người dùng** sẽ tương tác, dùng để sinh prompt test đa dạng.
Mỗi intent thường có một cặp **Easy** (hợp tác) và **Hard** (khó tính) tương phản nhau.

## Nguyên tắc
- **Easy persona**: hợp tác, diễn đạt rõ ràng, cung cấp đủ thông tin.
- **Hard persona**: mơ hồ, hay đổi ý, đặt câu hỏi ngược, thiếu kiên nhẫn.
- Tên + mô tả phải **cụ thể**, có tính cách riêng — tránh rập khuôn.
- Persona phải **bám sát intent**, không lạc sang nhu cầu khác.

## Ví dụ
| Loại | Mô tả |
|---|---|
| Easy | Sinh viên năm nhất, lịch sự, mô tả vấn đề đầy đủ từng bước |
| Hard | Phụ huynh bận rộn, nóng tính, hỏi cộc lốc, đòi kết quả ngay |

> Chỉnh guideline này trước khi bấm "Regenerate" Persona.
`;

export const SINGLE_TURN_GUIDELINE = `# Guideline tạo Single-turn Test Case

Single-turn test case là **một prompt duy nhất** thể hiện đúng persona + intent, dùng để
kiểm thử phản hồi của hệ thống AI.

## Nguyên tắc
- Viết ở **ngôi thứ nhất**, như chính người dùng đang nói.
- Phản ánh đúng **tính cách persona** và **mục tiêu của intent**.
- Ngắn gọn (1–3 câu), đủ ngữ cảnh để kích hoạt phản hồi rõ ràng.
- Tránh prompt chung chung có thể fit nhiều persona khác nhau.

## Ví dụ
- *Easy*: "Mình muốn đặt lịch học nhóm vào tối thứ 5, cho mình hướng dẫn các bước với ạ."
- *Hard*: "Sao tôi không đặt được lịch nhóm? Làm nhanh giúp tôi cái."

> Chỉnh guideline này trước khi bấm "Regenerate" Test Prompt.
`;
