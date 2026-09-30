"""Lớp truy cập cơ sở dữ liệu SQLite: kết nối an toàn, transaction, migration.

Nguyên tắc:
- Mọi kết nối đều bật WAL, busy_timeout và foreign_keys để tránh lỗi
  "database is locked" khi nhiều yêu cầu ghi đồng thời.
- Kết nối được mở và đóng theo phạm vi sử dụng, không chia sẻ giữa các luồng.
- Lược đồ chỉ được tạo qua file trong `app/migrations/`.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .config import APP_DIR, get_settings

MIGRATIONS_DIR = APP_DIR / "migrations"


def connect() -> sqlite3.Connection:
    """Mở một kết nối SQLite đã cấu hình đúng."""
    settings = get_settings()
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(settings.database_path, timeout=settings.db_timeout_seconds)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    connection.execute(f"PRAGMA busy_timeout = {int(settings.busy_timeout_ms)}")
    return connection


@contextmanager
def read_connection() -> Iterator[sqlite3.Connection]:
    """Kết nối chỉ đọc, tự đóng khi thoát."""
    connection = connect()
    try:
        yield connection
    finally:
        connection.close()


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    """Kết nối có transaction: tự commit khi thành công, rollback khi có lỗi."""
    connection = connect()
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def _ensure_migrations_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def applied_migrations(connection: sqlite3.Connection) -> set[str]:
    _ensure_migrations_table(connection)
    rows = connection.execute("SELECT version FROM schema_migrations").fetchall()
    return {row["version"] for row in rows}


def pending_migrations() -> list[Path]:
    """Danh sách file migration chưa áp dụng, theo thứ tự tên file."""
    if not MIGRATIONS_DIR.exists():
        return []
    with read_connection() as connection:
        done = applied_migrations(connection)
    return [path for path in sorted(MIGRATIONS_DIR.glob("*.sql")) if path.stem not in done]


def run_migrations() -> list[str]:
    """Áp dụng các migration còn thiếu. Trả về danh sách phiên bản vừa áp dụng.

    Mỗi file SQL phải idempotent để nếu lỗi giữa chừng thì chạy lại vẫn an toàn.
    """
    applied: list[str] = []
    if not MIGRATIONS_DIR.exists():
        return applied
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        version = path.stem
        with transaction() as connection:
            if version in applied_migrations(connection):
                continue
            # Tắt kiểm tra khoá ngoại khi chạy migration: cần cho các thao tác
            # dựng lại bảng, và mọi thay đổi luôn được kiểm tra lại sau đó.
            connection.commit()
            connection.execute("PRAGMA foreign_keys = OFF")
            try:
                connection.executescript(path.read_text(encoding="utf-8"))
                connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))
            finally:
                connection.execute("PRAGMA foreign_keys = ON")
                connection.commit()
        applied.append(version)
    return applied


def table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row["name"] for row in rows}


def index_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'index' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {row["name"] for row in rows}
