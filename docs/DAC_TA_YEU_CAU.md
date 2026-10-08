# ĐẶC TẢ YÊU CẦU PHẦN MỀM (SRS) — MINDORA

> Hệ thống Trợ lý học tập AI khai thác tài liệu. Bản rút gọn theo **code thực tế**
> (nhánh `feat/phase-0-1-foundation`, 08/10/2026). Chi tiết thiết kế:
> [`THIET_KE_HE_THONG.md`](./THIET_KE_HE_THONG.md). Cách chạy:
> [`HUONG_DAN_CHAY.md`](./HUONG_DAN_CHAY.md).

## 1. Giới thiệu

### 1.1. Mục đích

Người học tải tài liệu lên, hệ thống trích xuất nội dung và trả lời câu hỏi
**dựa trên chính tài liệu đó** (RAG + trích dẫn nguồn), đồng thời theo dõi
tiến độ học tập. Toàn bộ chạy **cục bộ, offline** sau khi cài đặt.

### 1.2. Phạm vi

| Trong phạm vi | Ngoài phạm vi (đã cắt so với SRS gốc) |
|---|---|
| Đăng ký/đăng nhập, phân quyền user/admin | Sinh quiz, làm bài, chấm điểm |
| Upload PDF/DOCX/XLSX/ảnh, OCR, gắn tag | Xuất hội thoại ra file |
| Hỏi đáp RAG kèm trích dẫn, tóm tắt | Tìm kiếm nâng cao trong lịch sử |
| Tiến độ theo số câu hỏi đã đặt | Khóa tài khoản tự động (mới chỉ ghi log) |
| Phản hồi học viên → admin trả lời | Tích hợp LMS |

### 1.3. Thuật ngữ

| Viết tắt | Nghĩa |
|---|---|
| RAG | Retrieval-Augmented Generation: tìm đoạn tài liệu liên quan rồi mới gọi LLM trả lời |
| Chunk | Đoạn văn bản 800 ký tự (chồng lấp 120) sau khi chia nhỏ tài liệu |
| Embedding | Vector 768 chiều của một đoạn văn, dùng để tìm kiếm ngữ nghĩa |
| OCR | Nhận dạng chữ trong ảnh/tài liệu scan (Tesseract, ngôn ngữ vie+eng) |

## 2. Mô tả tổng quan

### 2.1. Tác nhân

- **Học viên (User):** đăng ký, tải tài liệu của mình, hỏi đáp, xem tiến độ, gửi phản hồi.
- **Quản trị viên (Admin):** mọi quyền của User + quản lý tài khoản, cấu hình, thống kê, trả lời phản hồi.
- **Hệ thống:** tự trích xuất chữ, chia đoạn, sinh vector, cập nhật tiến độ sau mỗi lượt chat.

### 2.2. Kiến trúc

Web 3 tầng chạy trên một máy: **React + Vite** (`:5173`) → **FastAPI**
(`:8000`, Swagger `/docs`) → **Ollama** (`:11434`, model `qwen2.5:3b` chat +
`nomic-embed-text` embedding). Dữ liệu trong **1 file SQLite**, vector lưu
file `.vec`, file gốc lưu `app/storage`.

### 2.3. Ràng buộc chính

- Không Internet sau khi đã tải model; không dịch vụ trả phí; không tự huấn luyện model.
- Token phiên 7 ngày, lưu trình duyệt (`mindora_token`).
- Giới hạn upload mặc định 20 MB, cấu hình được.

## 3. Yêu cầu chức năng

### 3.1. Xác thực và phân quyền (E)

| Mã | Yêu cầu |
|---|---|
| FR-E1 | Đăng ký (tên 2–150, email 5–150, mật khẩu 8–128 ký tự), đăng nhập, đăng xuất; email trùng → 409 |
| FR-E2 | Phân quyền user/admin; admin không tự khóa/tự hạ quyền chính mình; khóa/mở tài khoản, đặt lại mật khẩu; đổi mật khẩu hoặc khóa → thu hồi toàn bộ phiên |
| FR-E3 | Admin xem/sửa cấu hình (`max_upload_mb`, `ai_model`, `embedding_model`); xem thống kê (tài khoản, hội thoại, câu hỏi, phản hồi mới); xem lịch sử hỏi của từng user; mọi thao tác ghi audit log |

### 3.2. Tài liệu (A)

| Mã | Yêu cầu |
|---|---|
| FR-A1 | Upload PDF/DOCX/XLSX/PNG/JPG/JPEG; kiểm tra đuôi file + dung lượng; trùng nội dung (hash) → 409 |
| FR-A2 | Tự trích xuất chữ: đọc trực tiếp, OCR nếu là ảnh/scan; ghi rõ cách trích xuất (`text`/`ocr`) |
| FR-A3 | Chia đoạn 800 ký tự (chồng lấp 120), sinh vector 768 chiều; trạng thái `uploading → ocr_processing → embedding → ready / error`, tự thử lại tối đa 3 lần |
| FR-A4 | Gắn tag môn/chương, xem danh sách, tìm kiếm, xem chi tiết, xem đoạn đã chia, tải file gốc, sửa metadata, xóa (xóa dây chuyền đoạn + vector + tóm tắt) |
| FR-A5 | Tóm tắt tài liệu: toàn văn / theo chương / tùy chọn |

### 3.3. Hỏi đáp (B)

| Mã | Yêu cầu |
|---|---|
| FR-B1 | Chat đa lượt, lưu lịch sử theo hội thoại, xem lại, xóa hội thoại; trả lời realtime qua SSE |
| FR-B2 | Hỏi trong 1 tài liệu (`document_id`) hoặc toàn bộ tài liệu `ready`; tìm đoạn liên quan bằng cosine (top-k, ngưỡng 0.35) |
| FR-B3 | Câu trả lời dựa trên ngữ cảnh, **kèm trích dẫn** (tên file, trang, đoạn trích, điểm tương đồng) |
| FR-B4 | Không đủ ngữ cảnh → trả lời "chưa đủ thông tin", không bịa (chống ảo giác) |
| FR-B5 | Giải bài tập từng bước dựa trên tài liệu (qua cùng luồng chat RAG) |

### 3.4. Tiến độ và phản hồi (F)

| Mã | Yêu cầu |
|---|---|
| FR-F1 | Mỗi lượt chat +1 câu hỏi cho môn của tài liệu (mặc định "Chung"); xem tổng quan (tài liệu/câu hỏi/hội thoại), tiến độ từng môn, hoạt động 84 ngày, gợi ý môn có tài liệu mà chưa hỏi |
| FR-F2 | Học viên gửi phản hồi (1–5 sao; bug/suggestion/praise/other; tối đa 2000 ký tự); admin đọc, đánh dấu đã đọc, trả lời |

## 4. Yêu cầu phi chức năng

| Mã | Yêu cầu | Đáp ứng |
|---|---|---|
| NFR-1 | Trả lời thông thường ≤ 5 giây | Ollama cục bộ + giữ model nạp sẵn 10 phút + SSE |
| NFR-2 | Dễ mở rộng lên PostgreSQL | Module tách lớp routers/repositories/services, migration có version |
| NFR-3 | Bảo mật | PBKDF2 310.000 vòng + salt, token 48 byte, chặn truy cập chéo (chỉ xem tài liệu của mình), SQL tham số hóa, React escape XSS |
| NFR-4 | Chống ảo giác | Trích dẫn nguồn + ngưỡng điểm + prompt bắt nói "chưa đủ thông tin" |
| NFR-5 | Ổn định | Máy trạng thái lỗi chi tiết, hàng đợi tự thử lại, endpoint `/api/health` |
| NFR-6 | Dễ dùng | Sidebar + thông báo lỗi tiếng Việt |
| NFR-7 | Dễ bảo trì | Code + migration + 114 test pytest + kiểm tra `ruff` |

## 5. Dữ liệu chính (15 bảng SQLite)

`users`, `sessions` (phiên 7 ngày), `system_settings` (cấu hình),
`audit_logs` (giữ lại khi xóa user), `conversations`, `messages`,
`message_citations` (trích dẫn), `documents` (trạng thái xử lý),
`chunks` (đoạn + đường dẫn vector), `document_summaries`,
`processing_jobs` (hàng đợi thử lại), `progress_stats` (khóa kép user+môn),
`feedback` (phản hồi + trả lời admin). Chưa dùng tới: `message_feedback`
(thích/không thích — mới tạo bảng, chưa có API), `login_attempts`
(mới ghi nhận lần đăng nhập, chưa khóa tự động). Toàn bộ khóa chính INTEGER tự tăng.

## 6. API chính (37 endpoint)

- Xác thực: `POST /api/auth/register|login|logout`, `GET /api/auth/me`
- Chat: `POST /api/chat|/api/chat/stream`, `GET /api/health`, CRUD `/api/conversations`
- Tài liệu: CRUD `/api/documents`, `/status`, `/download`, `/chunks`, `/summary`
- Tiến độ/phản hồi: `GET /api/progress`, `POST|GET /api/feedback`
- Admin: quản lý `/users`, `/settings`, `/stats`, `/feedback` (+reply), xem lịch sử user

## 7. Lịch sử cắt giảm (so với SRS gốc)

Module **Quiz/Bài tập** (sinh đề, làm bài, chấm điểm, tiến độ theo điểm số) đã bị
loại bỏ — migration `005` xóa 4 bảng quiz. Bù lại: tiến độ tính theo **số câu hỏi
đã đặt**, thêm **Phản hồi**. Dự trữ chưa dùng: `message_feedback` (mới tạo bảng,
chưa có API đánh giá), `quizzes_taken`, `best_score`, `study_minutes`,
`login_attempts` (mới ghi nhận, chưa khóa tự động) — giữ lại cho mở rộng sau.

