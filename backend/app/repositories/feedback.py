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
