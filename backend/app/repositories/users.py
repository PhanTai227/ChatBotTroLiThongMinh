"""Truy vấn bảng users.

Mọi câu truy vấn đều dùng tham số hoá để tránh SQL injection.
"""

from __future__ import annotations

import sqlite3

from ..db import read_connection, transaction


class EmailAlreadyExists(Exception):
    """Email đã được dùng để đăng ký."""


def create_user(full_name: str, email: str, password_hash: str) -> int:
    try:
        with transaction() as connection:
            cursor = connection.execute(
                "INSERT INTO users(full_name, email, password_hash) VALUES (?, ?, ?)",
                (full_name, email, password_hash),
            )
            return int(cursor.lastrowid)
    except sqlite3.IntegrityError as exc:
        raise EmailAlreadyExists from exc


def get_by_email(email: str) -> sqlite3.Row | None:
    with read_connection() as connection:
        return connection.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def get_by_id(user_id: int) -> sqlite3.Row | None:
    with read_connection() as connection:
        return connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def list_all() -> list[dict]:
    with read_connection() as connection:
        rows = connection.execute(
            "SELECT id, full_name, email, role, is_active, created_at, last_login_at "
            "FROM users ORDER BY created_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def set_role(user_id: int, role: str) -> None:
    with transaction() as connection:
        connection.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))


def set_active(user_id: int, is_active: bool) -> None:
    with transaction() as connection:
        connection.execute("UPDATE users SET is_active = ? WHERE id = ?", (int(is_active), user_id))


def set_password_hash(user_id: int, password_hash: str) -> None:
    with transaction() as connection:
        connection.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))


def delete_user(user_id: int) -> None:
    with transaction() as connection:
        connection.execute("DELETE FROM users WHERE id = ?", (user_id,))


def touch_last_login(user_id: int) -> None:
    with transaction() as connection:
        connection.execute("UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))


def count_all() -> int:
    with read_connection() as connection:
        return int(connection.execute("SELECT COUNT(*) FROM users").fetchone()[0])


def count_active() -> int:
    with read_connection() as connection:
        return int(connection.execute("SELECT COUNT(*) FROM users WHERE is_active = 1").fetchone()[0])


def count_admins() -> int:
    with read_connection() as connection:
        return int(connection.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0])
