"""Khởi tạo hệ thống khi khởi động: migration, sửa lược đồ cũ, dữ liệu nền."""

from __future__ import annotations

import logging
import sqlite3

from .config import get_settings
from .db import run_migrations, transaction
from .repositories import settings_repo
from .security import hash_password
from .services import documents as documents_service
from .services import storage

logger = logging.getLogger("mindora.bootstrap")


def _ensure_legacy_columns(connection: sqlite3.Connection) -> None:
    """Bổ sung cột còn thiếu của các phiên bản cũ (tương thích dữ liệu đã có)."""
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(conversations)")}
    if "user_id" not in columns:
        logger.info("Phát hiện conversations thiếu user_id, đang bổ sung.")
        connection.execute(
            "ALTER TABLE conversations ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE"
        )


def _ensure_admin_user(connection: sqlite3.Connection) -> int | None:
    """Tạo tài khoản quản trị mặc định khi cơ sở dữ liệu còn trống."""
    if connection.execute("SELECT 1 FROM users LIMIT 1").fetchone():
        return None
    settings = get_settings()
    connection.execute(
        "INSERT INTO users(full_name, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
        ("Quản trị viên", settings.default_admin_email, hash_password(settings.default_admin_password)),
    )
    logger.info("Đã tạo tài khoản quản trị mặc định: %s", settings.default_admin_email)
    return int(connection.execute("SELECT last_insert_rowid() AS id").fetchone()["id"])


def _backfill_conversation_owner(connection: sqlite3.Connection) -> int:
    """Gán chủ cho các hội thoại cũ chưa có user_id."""
    admin = connection.execute("SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1").fetchone()
    if not admin:
        return 0
    cursor = connection.execute(
        "UPDATE conversations SET user_id = ? WHERE user_id IS NULL", (admin["id"],)
    )
    return int(cursor.rowcount or 0)


def bootstrap() -> list[str]:
    """Chạy toàn bộ thao tác khởi tạo. Trả về danh sách migration vừa áp dụng."""
    applied = run_migrations()
    with transaction() as connection:
        _ensure_legacy_columns(connection)
        _ensure_admin_user(connection)
        migrated = _backfill_conversation_owner(connection)
    settings = get_settings()
    settings_repo.ensure_defaults(
        {
            "max_upload_mb": str(settings.default_max_upload_mb),
            "ai_model": settings.ollama_model,
        }
    )
    if applied:
        logger.info("Đã áp dụng migration: %s", ", ".join(applied))
    if migrated:
        logger.info("Đã gán chủ cho %d hội thoại cũ.", migrated)
    storage.ensure_storage_dirs()
    return applied


async def bootstrap_async() -> list[str]:
    """Khởi tạo rồi xử lý tiếp các việc tài liệu bị kẹt từ lần chạy trước.

    Việc này cần mạng cục bộ (Ollama) nên chạy sau khi phần CSDL đã sẵn sàng.
    """
    applied = bootstrap()
    await documents_service.recover_on_startup()
    return applied
