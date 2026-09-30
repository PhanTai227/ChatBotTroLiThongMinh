"""Kiểm thử lược đồ: schema.sql phải khớp với cơ sở dữ liệu sau khi chạy migration.

Mục tiêu: ngăn tình trạng sửa cơ sở dữ liệu mà không thêm migration, khiến tài liệu
lược đồ và mã nguồn lệch nhau.
"""

from __future__ import annotations

import re
from pathlib import Path

from app import db

SCHEMA_FILE = Path(__file__).resolve().parents[2] / "schema.sql"
INTERNAL_TABLES = {"sqlite_sequence", "schema_migrations"}
_CREATE_TABLE = re.compile(r"CREATE TABLE IF NOT EXISTS\s+(\w+)", re.IGNORECASE)


def _declared_tables() -> set[str]:
    text = SCHEMA_FILE.read_text(encoding="utf-8")
    return {match.group(1) for match in _CREATE_TABLE.finditer(text)}


def _database_tables() -> set[str]:
    with db.read_connection() as connection:
        return db.table_names(connection) - INTERNAL_TABLES


def test_schema_file_exists() -> None:
    assert SCHEMA_FILE.exists(), "Thiếu tệp schema.sql ở thư mục gốc."


def test_schema_sql_matches_database() -> None:
    actual = _database_tables()
    # Các bảng trung gian dùng để dựng lại bảng (hậu tố _new) không tồn tại sau migration.
    declared = {name for name in _declared_tables() if not (name.endswith("_new") and name not in actual)}
    assert declared == actual


def test_business_tables_are_present() -> None:
    expected = {
        "users",
        "sessions",
        "system_settings",
        "audit_logs",
        "conversations",
        "messages",
        "documents",
        "chunks",
        "document_summaries",
        "message_citations",
        "quizzes",
        "quiz_questions",
        "quiz_attempts",
        "quiz_answers",
        "progress_stats",
        "message_feedback",
        "processing_jobs",
        "login_attempts",
    }
    assert expected <= _database_tables()


def test_foreign_keys_enforced_for_business_tables() -> None:
    """Xoá tài liệu phải xoá luôn chunk và tóm tắt (ON DELETE CASCADE)."""
    from app.db import transaction

    with transaction() as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        user_id = connection.execute(
            "INSERT INTO users(full_name, email, password_hash) VALUES ('T', 'cascade@test.local', 'x')"
        ).lastrowid
        document_id = connection.execute(
            "INSERT INTO documents(owner_id, file_name, file_type, storage_path) "
            "VALUES (?, 't.pdf', 'pdf', 'storage/t.pdf')",
            (user_id,),
        ).lastrowid
        connection.execute(
            "INSERT INTO chunks(document_id, chunk_index, content) VALUES (?, 0, 'nội dung')",
            (document_id,),
        )
        connection.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        remaining = connection.execute(
            "SELECT COUNT(*) FROM chunks WHERE document_id = ?", (document_id,)
        ).fetchone()[0]
        assert int(remaining) == 0
        connection.execute("DELETE FROM users WHERE id = ?", (user_id,))
