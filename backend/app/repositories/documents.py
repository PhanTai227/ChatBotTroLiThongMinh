"""Truy vấn bảng documents."""

from __future__ import annotations

import sqlite3

from ..db import read_connection, transaction

STATUSES = ("uploading", "ocr_processing", "embedding", "ready", "error")

_COLUMNS = (
    "id, owner_id, file_name, file_type, mime_type, storage_path, content_hash, subject_tag, "
    "chapter_tag, status, error_message, file_size_kb, page_count, extract_method, "
    "created_at, updated_at"
)


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def create_document(
    owner_id: int,
    file_name: str,
    file_type: str,
    storage_path: str,
    content_hash: str,
    subject_tag: str | None = None,
    chapter_tag: str | None = None,
    mime_type: str | None = None,
) -> int:
    with transaction() as connection:
        cursor = connection.execute(
            "INSERT INTO documents(owner_id, file_name, file_type, storage_path, content_hash, "
            "subject_tag, chapter_tag, mime_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                owner_id,
                file_name,
                file_type,
                storage_path,
                content_hash,
                subject_tag,
                chapter_tag,
                mime_type,
            ),
        )
        return int(cursor.lastrowid)


def get_by_id(document_id: int) -> sqlite3.Row | None:
    with read_connection() as connection:
        return connection.execute(
            f"SELECT {_COLUMNS} FROM documents WHERE id = ?", (document_id,)
        ).fetchone()


def get_owned(document_id: int, owner_id: int) -> sqlite3.Row | None:
    with read_connection() as connection:
        return connection.execute(
            f"SELECT {_COLUMNS} FROM documents WHERE id = ? AND owner_id = ?",
            (document_id, owner_id),
        ).fetchone()


def find_by_hash(owner_id: int, content_hash: str) -> sqlite3.Row | None:
    with read_connection() as connection:
        return connection.execute(
            f"SELECT {_COLUMNS} FROM documents WHERE owner_id = ? AND content_hash = ?",
            (owner_id, content_hash),
        ).fetchone()


def _build_filters(
    owner_id: int,
    subject_tag: str | None = None,
    search: str | None = None,
    status: str | None = None,
) -> tuple[str, list[object]]:
    """Dựng điều kiện lọc dùng chung cho cả truy vấn lấy dữ liệu và đếm số bản ghi."""
    conditions = ["owner_id = ?"]
    params: list[object] = [owner_id]
    if subject_tag:
        conditions.append("subject_tag = ?")
        params.append(subject_tag)
    if status:
        conditions.append("status = ?")
        params.append(status)
    if search:
        conditions.append("(file_name LIKE ? OR chapter_tag LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    return " AND ".join(conditions), params


def list_for_owner(
    owner_id: int,
    subject_tag: str | None = None,
    search: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    where, params = _build_filters(owner_id, subject_tag, search, status)
    params.extend([limit, offset])
    with read_connection() as connection:
        rows = connection.execute(
            f"SELECT {_COLUMNS} FROM documents WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params,
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def count_for_owner(
    owner_id: int,
    subject_tag: str | None = None,
    search: str | None = None,
    status: str | None = None,
) -> int:
    """Đếm số tài liệu thoả điều kiện lọc, dùng cho phân trang phía giao diện."""
    where, params = _build_filters(owner_id, subject_tag, search, status)
    with read_connection() as connection:
        return int(connection.execute(f"SELECT COUNT(*) FROM documents WHERE {where}", params).fetchone()[0])


def set_storage(document_id: int, storage_path: str, file_size_kb: int) -> None:
    with transaction() as connection:
        connection.execute(
            "UPDATE documents SET storage_path = ?, file_size_kb = ?, status = 'ocr_processing', "
            "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (storage_path, file_size_kb, document_id),
        )


def set_status(
    document_id: int,
    status: str,
    error_message: str | None = None,
    page_count: int | None = None,
    extract_method: str | None = None,
) -> None:
    with transaction() as connection:
        connection.execute(
            "UPDATE documents SET status = ?, error_message = ?, page_count = COALESCE(?, page_count), "
            "extract_method = COALESCE(?, extract_method), updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, error_message, page_count, extract_method, document_id),
        )


def update_metadata(
    document_id: int,
    file_name: str | None = None,
    subject_tag: str | None = None,
    chapter_tag: str | None = None,
) -> None:
    fields: list[str] = []
    params: list[object] = []
    if file_name is not None:
        fields.append("file_name = ?")
        params.append(file_name.strip()[:255])
    if subject_tag is not None:
        fields.append("subject_tag = ?")
        params.append(subject_tag.strip()[:100] or None)
    if chapter_tag is not None:
        fields.append("chapter_tag = ?")
        params.append(chapter_tag.strip()[:150] or None)
    if not fields:
        return
    fields.append("updated_at = CURRENT_TIMESTAMP")
    params.append(document_id)
    with transaction() as connection:
        connection.execute(f"UPDATE documents SET {', '.join(fields)} WHERE id = ?", params)


def delete_document(document_id: int) -> None:
    with transaction() as connection:
        connection.execute("DELETE FROM documents WHERE id = ?", (document_id,))


def list_by_status(status: str, owner_id: int | None = None) -> list[dict]:
    """Tài liệu theo trạng thái; có owner_id thì giới hạn cho một người dùng."""
    where = "status = ?"
    params: list[object] = [status]
    if owner_id is not None:
        where += " AND owner_id = ?"
        params.append(owner_id)
    with read_connection() as connection:
        rows = connection.execute(
            f"SELECT {_COLUMNS} FROM documents WHERE {where} ORDER BY updated_at ASC", params
        ).fetchall()
    return [_row_to_dict(row) for row in rows]
