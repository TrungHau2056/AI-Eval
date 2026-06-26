# Tách Crawl ↔ Intent Discovery — Bàn giao cho Crawl Data Team

> Cập nhật: 2026-06-26 · Branch: `duong-UI`
> Trạng thái: **Đã xong & verified** (FE `tsc` ✅ · BE `py_compile` ✅ · `test_ingest_api` 4 passed)

## 1. Mục tiêu thay đổi

Trước đây nút social chạy `/api/crawl/{platform}` làm **crawl + extract intent** một lần. Nay tách đôi:

- **"Crawl Social Data"** (nút đen): chỉ crawl raw posts → hiển thị bảng *Social Media Crawl Results*. **Không** extract intent.
- **"Run Intent Discovery"** (nút cam): nút **duy nhất** sinh intent — từ mọi nguồn có sẵn (file upload / PRD / paste text / **dữ liệu social đã crawl**), cần ≥1 nguồn.

## 2. Hợp đồng API mới

### `POST /api/crawl/{facebook|threads|tiktok}`

**Request — field mới:**

| Field | Kiểu | Mặc định | Ý nghĩa |
|---|---|---|---|
| `extract_intents` | bool | `false` | `false` = crawl-only. `true` = giữ hành vi cũ (crawl + mine intent). FE luôn gửi `false`. |

**Response — field mới:**

| Field | Kiểu | Ý nghĩa |
|---|---|---|
| `crawl_posts` | `list[dict]` | Posts đã normalize cho bảng FE |

Mỗi item `crawl_posts`:

```json
{ "platform": "Facebook", "url": "...", "postingDate": "...", "text": "...", "likes": 0, "commentsCount": 0 }
```

**Side effect:** mỗi lần crawl lưu `state.raw_social_content = raw_content`. `/api/discover` sẽ tự gộp nội dung này + file/PRD/text khi mine intent.

### Normalizer

`_parse_posts()` trong [crawl.py](../backend/src/api/routers/crawl.py) đọc output JSON của crawler theo keys:
`postUrl`, `captionText`, `takenAtFormatted`, `likeCount`, `directReplyCount`.
→ **Cả 3 crawler hiện đều xuất đúng keys này, không cần sửa crawler.**

## 3. Luồng người dùng mới

1. Tick nền tảng (Facebook/Threads/TikTok) → **Crawl Social Data** → raw posts hiện ở bảng; `state.intents` **không đổi**.
2. **Run Intent Discovery** → extract intent từ file/PRD/text **+ dữ liệu social đã crawl** (backend tự gộp) → tự chuyển sang Curation.

## 4. Giới hạn / phần còn giả lập

1. **Apify token bắt buộc.** Thiếu `APIFY_TOKEN` (env hoặc request body) → endpoint trả **400**. Khi đó FE dùng **demo fallback** (sinh vài dòng mẫu từ keywords) để bảng không trống → **dữ liệu demo, không phải thật**.
2. **Multi-platform mới là UI-only.** Chọn nhiều nền tảng nhưng backend chỉ crawl **1 endpoint** (ưu tiên `threads > tiktok > facebook`, theo slug mapping trong `handleCrawlSocial` — [App.tsx](../frontend/src/App.tsx)).
3. **Label nguồn intent (Facebook/TikTok/Threads/Data/PRD): chưa làm.** `/api/discover` hiện chỉ nối nội dung, không gắn nhãn nguồn.

## 5. Việc tiếp theo cho Crawl Data Team

- [ ] Cấu hình & kiểm tra `APIFY_TOKEN` để crawl thật; xác nhận `crawl_posts` có đủ `postingDate` / `likes` / `commentsCount` (một số actor có thể thiếu ngày đăng).
- [ ] Quyết định có cần **crawl thật nhiều nền tảng song song** không — nếu có: sửa `handleCrawlSocial` lặp qua từng platform + (tùy chọn) endpoint backend gộp kết quả.
- [ ] (Tùy chọn) Cho crawler trả thẳng structured posts thay vì để backend parse JSON string — bớt một lớp chuyển đổi.
- [ ] Bật `extract_intents:true` cho luồng nào muốn crawl + mine cùng lúc (nếu cần).
- [ ] Hạng mục sau: gắn `source` cho intent để Curation hiển thị nguồn.

## 6. File đã thay đổi

**Backend**
- [backend/src/models/schemas.py](../backend/src/models/schemas.py) — thêm `raw_social_content` vào `PipelineState`
- [backend/src/api/routers/crawl.py](../backend/src/api/routers/crawl.py) — `extract_intents`, `crawl_posts`, `_parse_posts`, lưu `raw_social_content`
- [backend/src/api/routers/frontend_api.py](../backend/src/api/routers/frontend_api.py) — `/api/discover` gộp `raw_social_content`

**Frontend**
- [frontend/src/App.tsx](../frontend/src/App.tsx) — `handleCrawlSocial` (crawl-only), rewire prop `onCrawlSocial`
- [frontend/src/components/DataIngestionTab.tsx](../frontend/src/components/DataIngestionTab.tsx) — nút "Crawl Social Data", `handleCrawlSubmit`, banner crawl-centric

## 7. Cách kiểm thử nhanh

```bash
# Frontend typecheck
cd frontend && npx tsc --noEmit

# Backend compile + ingest test
cd backend && python -m py_compile src/models/schemas.py src/api/routers/crawl.py src/api/routers/frontend_api.py
python -m pytest tests/test_ingest_api.py -q
```

Manual (`npm run dev`): tick platform → **Crawl Social Data** → bảng có raw posts (thật nếu có Apify token, demo nếu không); `state.intents` không đổi. Sau đó **Run Intent Discovery** → intent sinh từ dữ liệu social đã crawl (+ file/PRD/text nếu có). Không chọn nền tảng → cảnh báo "Please select at least one social platform".
