"""Truy vấn phản hồi / đánh giá của học viên gửi tới quản trị viên."""

from __future__ import annotations

import sqlite3

from ..db import read_connection, transaction


def create(user_id: int, rating: int, category: str, content: str) -> dict:
    with transaction() as connection:
        cursor = connection.execute(
            """INSERT INTO feedback(user_id, rating, category, content)
               VALUES (?, ?, ?, ?)""",
            (user_id, rating, category, content),
        )
        feedback_id = int(cursor.lastrowid)
        row = connection.execute("SELECT * FROM feedback WHERE id = ?", (feedback_id,)).fetchone()
    return dict(row)


def list_for_user(user_id: int) -> list[dict]:
    with read_connection() as connection:
        rows = connection.execute(
            """SELECT id, rating, category, content, status, admin_reply, created_at, updated_at
               FROM feedback WHERE user_id = ? ORDER BY id DESC""",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def list_all() -> list[dict]:
    """Toàn bộ phản hồi kèm thông tin người gửi, mới nhất trước (dành cho admin)."""
    with read_connection() as connection:
        rows = connection.execute(
            """SELECT f.id, f.rating, f.category, f.content, f.status, f.admin_reply,
                      f.created_at, f.updated_at,
                      u.id AS user_id, u.full_name, u.email
               FROM feedback f
               JOIN users u ON u.id = f.user_id
               ORDER BY f.id DESC"""
        ).fetchall()
    return [dict(row) for row in rows]


def get(feedback_id: int) -> sqlite3.Row | None:
    with read_connection() as connection:
        return connection.execute("SELECT * FROM feedback WHERE id = ?", (feedback_id,)).fetchone()


def set_status(feedback_id: int, status: str) -> bool:
    with transaction() as connection:
        cursor = connection.execute(
            "UPDATE feedback SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, feedback_id),
        )
        return bool(cursor.rowcount)


def reply(feedback_id: int, admin_reply: str) -> bool:
    with transaction() as connection:
        cursor = connection.execute(
            """UPDATE feedback SET admin_reply = ?, status = 'replied', updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (admin_reply, feedback_id),
        )
        return bool(cursor.rowcount)


def count_new() -> int:
    with read_connection() as connection:
        return int(connection.execute("SELECT COUNT(*) FROM feedback WHERE status = 'new'").fetchone()[0])


def rate_message(message_id: int, user_id: int, rating: int) -> bool:
    """Lưu hoặc đổi đánh giá của người dùng cho một câu trả lời AI của họ."""
    with transaction() as connection:
        allowed = connection.execute(
            """SELECT 1 FROM messages m JOIN conversations c ON c.id = m.conversation_id
               WHERE m.id = ? AND m.role = 'assistant' AND (c.user_id = ? OR c.user_id IS NULL)""",
            (message_id, user_id),
        ).fetchone()
        if not allowed:
            return False
        connection.execute(
            """INSERT INTO message_feedback(message_id, user_id, rating) VALUES (?, ?, ?)
               ON CONFLICT(message_id, user_id) DO UPDATE SET rating = excluded.rating,
               created_at = CURRENT_TIMESTAMP""",
            (message_id, user_id, rating),
        )
    return True


def list_message_ratings() -> list[dict]:
    """Đánh giá câu trả lời AI kèm câu hỏi gần nhất để quản trị viên xem ngữ cảnh."""
    with read_connection() as connection:
        rows = connection.execute(
            """SELECT mf.id, mf.message_id, mf.rating, mf.created_at,
                      m.content AS answer, u.id AS user_id, u.full_name, u.email,
                      (SELECT previous.content FROM messages previous
                       WHERE previous.conversation_id = m.conversation_id
                         AND previous.role = 'user' AND previous.id < m.id
                       ORDER BY previous.id DESC LIMIT 1) AS question
               FROM message_feedback mf
               JOIN messages m ON m.id = mf.message_id
               JOIN users u ON u.id = mf.user_id
               ORDER BY mf.id DESC"""
        ).fetchall()
    return [dict(row) for row in rows]
