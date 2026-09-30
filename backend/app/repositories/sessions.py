"""Truy vấn bảng sessions (phiên đăng nhập)."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

from ..db import read_connection, transaction


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def create_session(user_id: int, token: str, days: int) -> str:
    expires_at = (datetime.now(UTC) + timedelta(days=days)).isoformat()
    with transaction() as connection:
        connection.execute(
            "INSERT INTO sessions(token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires_at),
        )
    return expires_at


def delete_session(token: str) -> None:
    with transaction() as connection:
        connection.execute("DELETE FROM sessions WHERE token = ?", (token,))


def delete_sessions_for_user(user_id: int) -> None:
    with transaction() as connection:
        connection.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))


def find_user_by_token(token: str) -> sqlite3.Row | None:
    """Trả về thông tin người dùng nếu token còn hiệu lực."""
    with read_connection() as connection:
        return connection.execute(
            """SELECT u.id, u.full_name, u.email, u.role, u.is_active
               FROM sessions s JOIN users u ON u.id = s.user_id
               WHERE s.token = ? AND s.expires_at > ?""",
            (token, _now_iso()),
        ).fetchone()


def purge_expired() -> int:
    """Xoá phiên đã hết hạn, trả về số bản ghi đã xoá."""
    with transaction() as connection:
        cursor = connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (_now_iso(),))
        return int(cursor.rowcount or 0)


def count_active() -> int:
    with read_connection() as connection:
        return int(
            connection.execute(
                "SELECT COUNT(*) FROM sessions WHERE expires_at > ?", (_now_iso(),)
            ).fetchone()[0]
        )
