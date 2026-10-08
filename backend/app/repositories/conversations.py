"""Truy vấn bảng conversations và messages."""

from __future__ import annotations

import sqlite3

from ..db import read_connection, transaction

TITLE_MAX_LENGTH = 60


def create_conversation(user_id: int, title: str) -> int:
    with transaction() as connection:
        cursor = connection.execute(
            "INSERT INTO conversations(user_id, title) VALUES (?, ?)",
            (user_id, title[:TITLE_MAX_LENGTH]),
        )
        return int(cursor.lastrowid)


def get_conversation(conversation_id: int) -> sqlite3.Row | None:
    with read_connection() as connection:
        return connection.execute(
            "SELECT id, user_id, title, created_at FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()


def is_accessible(conversation_id: int, user_id: int) -> bool:
    """Hội thoại thuộc về người dùng, hoặc còn chưa gán chủ (dữ liệu cũ)."""
    with read_connection() as connection:
        row = connection.execute(
            "SELECT 1 FROM conversations WHERE id = ? AND (user_id = ? OR user_id IS NULL)",
            (conversation_id, user_id),
        ).fetchone()
    return row is not None


def add_message(conversation_id: int, role: str, content: str) -> int:
    with transaction() as connection:
        cursor = connection.execute(
            "INSERT INTO messages(conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, role, content),
        )
        return int(cursor.lastrowid)


def list_messages(conversation_id: int) -> list[dict]:
    with read_connection() as connection:
        rows = connection.execute(
            "SELECT id, role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY id",
            (conversation_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def list_for_user(user_id: int, limit: int = 50, offset: int = 0) -> list[dict]:
    with read_connection() as connection:
        rows = connection.execute(
            """SELECT c.id, c.title, c.created_at,
                      (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count
               FROM conversations c
               WHERE c.user_id = ?
               ORDER BY c.created_at DESC
               LIMIT ? OFFSET ?""",
            (user_id, limit, offset),
        ).fetchall()
    return [dict(row) for row in rows]


def count_all() -> int:
    with read_connection() as connection:
        return int(connection.execute("SELECT COUNT(*) FROM conversations").fetchone()[0])


def count_user_messages() -> int:
    with read_connection() as connection:
        return int(connection.execute("SELECT COUNT(*) FROM messages WHERE role = 'user'").fetchone()[0])


class ConversationNotFound(Exception):
    """Không tìm thấy hội thoại hoặc người dùng không có quyền truy cập."""


def delete_conversation(conversation_id: int, user_id: int) -> bool:
    """Xoá hội thoại của chính người dùng. Trả về False nếu không tìm thấy."""
    with transaction() as connection:
        cursor = connection.execute(
            "DELETE FROM conversations WHERE id = ? AND (user_id = ? OR user_id IS NULL)",
            (conversation_id, user_id),
        )
        return bool(cursor.rowcount)


def start_turn(user_id: int, message: str, conversation_id: int | None) -> int:
    """Mở lượt hỏi đáp: tạo hội thoại nếu cần và lưu câu hỏi, trong cùng một transaction.

    Trả về conversation_id. Ném ConversationNotFound nếu hội thoại không thuộc về user.
    """
    with transaction() as connection:
        if conversation_id is None:
            cursor = connection.execute(
                "INSERT INTO conversations(user_id, title) VALUES (?, ?)",
                (user_id, message[:TITLE_MAX_LENGTH]),
            )
            resolved_id = int(cursor.lastrowid)
        else:
            allowed = connection.execute(
                "SELECT 1 FROM conversations WHERE id = ? AND (user_id = ? OR user_id IS NULL)",
                (conversation_id, user_id),
            ).fetchone()
            if not allowed:
                raise ConversationNotFound
            resolved_id = conversation_id
        connection.execute(
            "INSERT INTO messages(conversation_id, role, content) VALUES (?, 'user', ?)",
            (resolved_id, message),
        )
    return resolved_id
