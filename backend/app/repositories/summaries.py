"""Truy vấn bảng document_summaries (Module C — tóm tắt tài liệu)."""

from __future__ import annotations

from ..db import read_connection, transaction


def get_cached(document_id: int, summary_type: str = "document", target_label: str | None = None) -> dict | None:
    with read_connection() as connection:
        row = connection.execute(
            """SELECT id, document_id, summary_type, target_label, content, created_at
               FROM document_summaries
               WHERE document_id = ? AND summary_type = ? AND IFNULL(target_label, '') = IFNULL(?, '')""",
            (document_id, summary_type, target_label),
        ).fetchone()
    return dict(row) if row else None


def save(
    document_id: int, content: str, summary_type: str = "document", target_label: str | None = None
) -> dict:
    """Ghi tóm tắt; nếu đã có thì thay nội dung mới (INSERT OR REPLACE theo chỉ mục duy nhất)."""
    with transaction() as connection:
        connection.execute(
            """INSERT OR REPLACE INTO document_summaries(document_id, summary_type, target_label, content)
               VALUES (?, ?, ?, ?)""",
            (document_id, summary_type, target_label, content),
        )
        row = connection.execute(
            """SELECT id, document_id, summary_type, target_label, content, created_at
               FROM document_summaries
               WHERE document_id = ? AND summary_type = ? AND IFNULL(target_label, '') = IFNULL(?, '')""",
            (document_id, summary_type, target_label),
        ).fetchone()
    return dict(row) if row else {"document_id": document_id, "content": content}
