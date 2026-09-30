"""Truy vấn bảng system_settings."""

from __future__ import annotations

from ..db import read_connection, transaction

ALLOWED_KEYS = ("max_upload_mb", "ai_model")


def get_value(key: str, default: str | None = None) -> str | None:
    with read_connection() as connection:
        row = connection.execute("SELECT value FROM system_settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def get_int(key: str, default: int) -> int:
    raw = get_value(key)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


def list_all() -> list[dict]:
    with read_connection() as connection:
        rows = connection.execute("SELECT key, value, updated_at FROM system_settings ORDER BY key").fetchall()
    return [dict(row) for row in rows]


def set_value(key: str, value: str) -> None:
    with transaction() as connection:
        connection.execute(
            "UPDATE system_settings SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE key = ?",
            (value, key),
        )


def ensure_defaults(defaults: dict[str, str]) -> None:
    """Thêm các khoá còn thiếu mà không ghi đè giá trị người dùng đã đặt."""
    if not defaults:
        return
    with transaction() as connection:
        connection.executemany(
            "INSERT OR IGNORE INTO system_settings(key, value) VALUES (?, ?)",
            list(defaults.items()),
        )
