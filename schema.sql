-- LƯỢC ĐỒ CƠ SỞ DỮ LIỆU - HỆ THỐNG MINDORA
-- Tệp này được SINH TỰ ĐỘNG từ backend/app/migrations, không được sửa tay.
-- Sinh lại bằng lệnh: python scripts/export-schema.py
-- Ngày sinh: 2026-09-30
--
-- Quyết định thiết kế: khoá chính dùng INTEGER AUTOINCREMENT thay vì UUID TEXT để
-- giữ nguyên dữ liệu đang có và thuận tiện chuyển sang PostgreSQL sau này.
-- Ràng buộc CHECK/UNIQUE được đặt ở tầng cơ sở dữ liệu để dữ liệu luôn hợp lệ.


-- ============ 001_baseline ===========
-- 001_baseline: lược đồ nền cho nghiệp vụ xác thực, hội thoại và quản trị.
-- File này thay thế hoàn toàn hàm init_database() trước đây.
-- Nguyên tắc: mọi câu lệnh phải idempotent để có thể chạy lại an toàn.

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('user', 'admin')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER,
    action TEXT NOT NULL,
    target_user_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(admin_id) REFERENCES users(id),
    FOREIGN KEY(target_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    title TEXT NOT NULL DEFAULT 'Cuộc hội thoại mới',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- Chỉ mục phục vụ truy vấn thường gặp: lịch sử hội thoại, kiểm tra phiên, nhật ký.
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);

-- ============ 002_audit_logs_keep_history ===========
-- 002_audit_logs_keep_history: giữ lại nhật ký thao tác khi người dùng bị xoá.
--
-- Vấn đề: audit_logs.target_user_id tham chiếu users(id) mà không khai báo ON DELETE.
-- Khi quản trị viên xoá một tài khoản đã từng có nhật ký, SQLite ném lỗi ràng buộc
-- khóa ngoại và thao tác xoá thất bại. Cách đúng là giữ dòng nhật ký và đặt
-- các khoá tham chiếu về NULL (ON DELETE SET NULL).
--
-- SQLite không sửa được khoá ngoại của bảng đã tồn tại nên phải dựng lại bảng.

CREATE TABLE IF NOT EXISTS audit_logs_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER,
    action TEXT NOT NULL,
    target_user_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(admin_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY(target_user_id) REFERENCES users(id) ON DELETE SET NULL
);

INSERT OR IGNORE INTO audit_logs_new(id, admin_id, action, target_user_id, created_at)
    SELECT id, admin_id, action, target_user_id, created_at FROM audit_logs;

DROP TABLE audit_logs;

ALTER TABLE audit_logs_new RENAME TO audit_logs;

CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);

-- ============ 003_audit_logs_detail ===========
-- 003_audit_logs_detail: lưu thêm thông tin mô tả cho dòng nhật ký.
--
-- Khi một tài khoản bị xoá, không thể giữ khoá ngoại tới tài khoản đó (dòng nhật ký
-- phải tồn tại độc lập với vòng đời người dùng). Vì vậy thông tin định danh người
-- bị xoá được lưu ở cột detail dạng văn bản.

ALTER TABLE audit_logs ADD COLUMN detail TEXT;

-- ============ 004_business_schema ===========
-- 004_business_schema: lược đồ nghiệp vụ của Mindora.
--
-- Quyết định thiết kế: khoá chính dùng INTEGER AUTOINCREMENT (không dùng UUID TEXT) để
-- giữ nguyên dữ liệu đang có và dễ chuyển sang PostgreSQL (GENERATED ALWAYS AS IDENTITY).
-- Mọi bảng nghiệp vụ đều khai báo ràng buộc CHECK/UNIQUE ở tầng cơ sở dữ liệu để dữ liệu
-- luôn hợp lệ dù ứng dụng có lỗi.

-- 1. Tài liệu: hồ sơ tệp đã tải lên và trạng thái xử lý
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL,
    file_name TEXT NOT NULL CHECK(length(trim(file_name)) BETWEEN 1 AND 255),
    file_type TEXT NOT NULL CHECK(file_type IN ('pdf', 'docx', 'xlsx', 'image')),
    mime_type TEXT,
    storage_path TEXT NOT NULL,
    content_hash TEXT,
    subject_tag TEXT CHECK(subject_tag IS NULL OR length(subject_tag) <= 100),
    chapter_tag TEXT CHECK(chapter_tag IS NULL OR length(chapter_tag) <= 150),
    status TEXT NOT NULL DEFAULT 'uploading'
        CHECK(status IN ('uploading', 'ocr_processing', 'embedding', 'ready', 'error')),
    error_message TEXT,
    file_size_kb INTEGER CHECK(file_size_kb IS NULL OR file_size_kb >= 0),
    page_count INTEGER CHECK(page_count IS NULL OR page_count >= 0),
    extract_method TEXT CHECK(extract_method IS NULL OR extract_method IN ('text', 'ocr')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(owner_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_owner_hash ON documents(owner_id, content_hash);
CREATE INDEX IF NOT EXISTS idx_documents_owner_status ON documents(owner_id, status);

-- 2. Đoạn văn bản sau khi chia nhỏ, dùng cho tìm kiếm ngữ nghĩa
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL CHECK(chunk_index >= 0),
    content TEXT NOT NULL CHECK(length(trim(content)) > 0),
    vector_ref TEXT,
    page_number INTEGER CHECK(page_number IS NULL OR page_number >= 1),
    token_count INTEGER CHECK(token_count IS NULL OR token_count >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, chunk_index),
    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);

-- 3. Tóm tắt tài liệu hoặc từng chương
CREATE TABLE IF NOT EXISTS document_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    summary_type TEXT NOT NULL DEFAULT 'chapter'
        CHECK(summary_type IN ('document', 'chapter', 'custom')),
    target_label TEXT,
    content TEXT NOT NULL CHECK(length(trim(content)) > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_document_summaries_unique
    ON document_summaries(document_id, summary_type, IFNULL(target_label, ''));

-- 4. Nguồn trích dẫn cho từng câu trả lời của AI
CREATE TABLE IF NOT EXISTS message_citations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    document_id INTEGER,
    chunk_id INTEGER,
    file_name TEXT,
    page_number INTEGER,
    snippet TEXT,
    score REAL,
    position INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(message_id) REFERENCES messages(id) ON DELETE CASCADE,
    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE SET NULL,
    FOREIGN KEY(chunk_id) REFERENCES chunks(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_message_citations_message ON message_citations(message_id);

-- 5. Tiến độ học tập theo môn học
CREATE TABLE IF NOT EXISTS progress_stats (
    user_id INTEGER NOT NULL,
    subject_tag TEXT NOT NULL CHECK(length(trim(subject_tag)) BETWEEN 1 AND 100),
    study_minutes INTEGER NOT NULL DEFAULT 0 CHECK(study_minutes >= 0),
    questions_asked INTEGER NOT NULL DEFAULT 0 CHECK(questions_asked >= 0),
    quizzes_taken INTEGER NOT NULL DEFAULT 0 CHECK(quizzes_taken >= 0),
    best_score INTEGER CHECK(best_score IS NULL OR best_score >= 0),
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(user_id, subject_tag),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 6. Đánh giá của người dùng với câu trả lời của AI (cơ sở dữ liệu huấn luyện)
CREATE TABLE IF NOT EXISTS message_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    rating INTEGER NOT NULL CHECK(rating IN (-1, 1)),
    note TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(message_id, user_id),
    FOREIGN KEY(message_id) REFERENCES messages(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 7. Hàng đợi xử lý nền (OCR, vector nhúng, tóm tắt) có tự thử lại
CREATE TABLE IF NOT EXISTS processing_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    stage TEXT NOT NULL CHECK(stage IN ('ocr', 'embedding', 'summary')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'running', 'done', 'error')),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK(attempts >= 0),
    last_error TEXT,
    next_retry_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_processing_jobs_status ON processing_jobs(status, next_retry_at);

-- 8. Theo dõi số lần đăng nhập sai để khoá tài khoản tạm thời
CREATE TABLE IF NOT EXISTS login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    ip TEXT,
    success INTEGER NOT NULL CHECK(success IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_login_attempts_email ON login_attempts(email, created_at);

-- ============ 005_remove_quizzes_add_feedback ===========
-- 005_remove_quizzes_add_feedback: bỏ module Quiz/Bài tập, thêm phản hồi gửi quản trị.

-- Phản hồi / đánh giá của học viên gửi tới quản trị viên.
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    category TEXT NOT NULL DEFAULT 'other'
        CHECK(category IN ('bug', 'suggestion', 'praise', 'other')),
    content TEXT NOT NULL CHECK(length(trim(content)) BETWEEN 1 AND 2000),
    status TEXT NOT NULL DEFAULT 'new' CHECK(status IN ('new', 'read', 'replied')),
    admin_reply TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_feedback_status ON feedback(status, created_at);
