-- 005_remove_quizzes_add_feedback: loại bỏ module Quiz/Bài tập, bổ sung phản hồi gửi admin.
--
-- Lý do: dự án thu hẹp trọng tâm vào nghiệp vụ hỏi đáp RAG. Bảng quiz_answers tham chiếu
-- quiz_questions nên phải drop theo đúng thứ tự khoá ngoại (foreign_keys đang bị tắt khi
-- chạy migration nên thứ tự chỉ nhằm mục đích rõ nghĩa).

DROP TABLE IF EXISTS quiz_answers;
DROP TABLE IF EXISTS quiz_attempts;
DROP TABLE IF EXISTS quiz_questions;
DROP TABLE IF EXISTS quizzes;

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