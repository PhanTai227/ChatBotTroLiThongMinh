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

-- 5. Bộ quiz sinh từ tài liệu
CREATE TABLE IF NOT EXISTS quizzes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    document_id INTEGER,
    title TEXT NOT NULL CHECK(length(trim(title)) BETWEEN 1 AND 255),
    quiz_type TEXT NOT NULL DEFAULT 'multiple_choice'
        CHECK(quiz_type IN ('multiple_choice', 'true_false', 'short_answer')),
    difficulty TEXT NOT NULL DEFAULT 'medium' CHECK(difficulty IN ('easy', 'medium', 'hard')),
    question_count INTEGER NOT NULL DEFAULT 0 CHECK(question_count >= 0),
    duration_minutes INTEGER CHECK(duration_minutes IS NULL OR duration_minutes > 0),
    status TEXT NOT NULL DEFAULT 'ready' CHECK(status IN ('processing', 'ready', 'error')),
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_quizzes_user ON quizzes(user_id, created_at);

CREATE TABLE IF NOT EXISTS quiz_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id INTEGER NOT NULL,
    position INTEGER NOT NULL CHECK(position >= 0),
    content TEXT NOT NULL CHECK(length(trim(content)) > 0),
    options_json TEXT,
    correct_option INTEGER CHECK(correct_option IS NULL OR correct_option BETWEEN 0 AND 3),
    correct_answer TEXT,
    explanation TEXT,
    page_number INTEGER,
    UNIQUE(quiz_id, position),
    FOREIGN KEY(quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
);

-- 6. Lượt làm bài và kết quả (chỉ ghi thêm, không sửa lịch sử)
CREATE TABLE IF NOT EXISTS quiz_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    score INTEGER NOT NULL DEFAULT 0 CHECK(score >= 0),
    max_score INTEGER NOT NULL DEFAULT 0 CHECK(max_score >= 0),
    duration_seconds INTEGER CHECK(duration_seconds IS NULL OR duration_seconds >= 0),
    submitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user ON quiz_attempts(user_id, submitted_at);

CREATE TABLE IF NOT EXISTS quiz_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    selected_option INTEGER,
    is_correct INTEGER NOT NULL CHECK(is_correct IN (0, 1)),
    FOREIGN KEY(attempt_id) REFERENCES quiz_attempts(id) ON DELETE CASCADE,
    FOREIGN KEY(question_id) REFERENCES quiz_questions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_quiz_answers_attempt ON quiz_answers(attempt_id);


-- 7. Tiến độ học tập theo môn học
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

-- 8. Đánh giá của người dùng với câu trả lời của AI (cơ sở dữ liệu huấn luyện)
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

-- 9. Hàng đợi xử lý nền (OCR, vector nhúng, tóm tắt) có tự thử lại
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

-- 10. Theo dõi số lần đăng nhập sai để khoá tài khoản tạm thời
CREATE TABLE IF NOT EXISTS login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    ip TEXT,
    success INTEGER NOT NULL CHECK(success IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_login_attempts_email ON login_attempts(email, created_at);

