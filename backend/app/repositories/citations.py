"""Ghi và đọc nguồn trích dẫn của câu trả lời AI (bảng message_citations).

Vì sao cần bảng riêng: một câu trả lời có nhiều nguồn và một đoạn văn bản có thể
được trích dẫn trong nhiều câu trả lời, nên đây là quan hệ nhiều-nhiều.
"""

from __future__ import annotations

from ..db import read_connection, transaction


def add_citations(message_id: int, citations: list[tuple[int | None, int | None, str, int | None, str, float]]) -> int:
    """Lưu danh sách nguồn của một câu trả lời.

    Mỗi phần tử gồm: (document_id, chunk_id, file_name, page_number, snippet, score).
    """
    if not citations:
        return 0
    sql = (
        "INSERT INTO message_citations"
        "(message_id, document_id, chunk_id, file_name, page_number, snippet, score, position) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    )
    with transaction() as connection:
        connection.executemany(
            sql,
            [
                (message_id, document_id, chunk_id, file_name, page_number, snippet[:500], score, position)
                for position, (document_id, chunk_id, file_name, page_number, snippet, score) in enumerate(citations)
            ],
        )
    return len(citations)


def list_for_message(message_id: int) -> list[dict]:
    with read_connection() as connection:
        rows = connection.execute(
            "SELECT document_id, chunk_id, file_name, page_number, snippet, score, position "
            "FROM message_citations WHERE message_id = ? ORDER BY position",
            (message_id,),
        ).fetchall()
    return [dict(row) for row in rows]
