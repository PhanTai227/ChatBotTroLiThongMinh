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
