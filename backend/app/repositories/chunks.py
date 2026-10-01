"""Truy vấn bảng chunks (đoạn văn bản của tài liệu)."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable

from ..db import read_connection, transaction

_COLUMNS = "id, document_id, chunk_index, content, vector_ref, page_number, token_count, created_at"


def replace_chunks(
    document_id: int,
    chunks: Iterable[tuple[int, str, int | None, int]],
) -> int:
    """Thay toàn bộ đoạn của tài liệu trong một transaction (xử lý lại tài liệu là an toàn)."""
    items = list(chunks)
    with transaction() as connection:
        connection.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
        connection.executemany(
            "INSERT INTO chunks(document_id, chunk_index, content, page_number, token_count) "
            "VALUES (?, ?, ?, ?, ?)",
            [(document_id, index, content, page, tokens) for index, content, page, tokens in items],
        )
    return len(items)


def count_for_document(document_id: int) -> int:
    with read_connection() as connection:
        return int(
            connection.execute("SELECT COUNT(*) FROM chunks WHERE document_id = ?", (document_id,)).fetchone()[0]
        )


def list_for_document(document_id: int, limit: int = 200, offset: int = 0) -> list[dict]:
    with read_connection() as connection:
        rows = connection.execute(
            f"SELECT {_COLUMNS} FROM chunks WHERE document_id = ? ORDER BY chunk_index LIMIT ? OFFSET ?",
            (document_id, limit, offset),
        ).fetchall()
    return [dict(row) for row in rows]


def get_by_ids(chunk_ids: list[int]) -> list[sqlite3.Row]:
    if not chunk_ids:
        return []
    placeholders = ",".join("?" for _ in chunk_ids)
    with read_connection() as connection:
        return connection.execute(
            f"SELECT {_COLUMNS} FROM chunks WHERE id IN ({placeholders})", chunk_ids
        ).fetchall()
