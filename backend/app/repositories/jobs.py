"""Hàng đợi xử lý nền lưu trong bảng processing_jobs.

Vì sao dùng hàng đợi trong CSDL thay vì hàng đợi trong bộ nhớ:
- Không mất công việc khi tiến trình bị tắt giữa chừng (có thể đưa lại vào hàng đợi lúc khởi động).
- Có lịch sử và số lần thử lại, dễ kiểm tra và báo lỗi cho người dùng.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

from ..db import read_connection, transaction

STAGE_OCR = "ocr"


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(moment: datetime) -> str:
    return moment.isoformat()


def enqueue(document_id: int, stage: str = STAGE_OCR) -> int:
    with transaction() as connection:
        cursor = connection.execute(
            "INSERT INTO processing_jobs(document_id, stage, status) VALUES (?, ?, 'pending')",
            (document_id, stage),
        )
        return int(cursor.lastrowid)


def claim_next(stage: str = STAGE_OCR) -> sqlite3.Row | None:
    """Lấy một việc đang chờ và đánh dấu đang chạy. Trả về None nếu không có việc."""
    with transaction() as connection:
        row = connection.execute(
            "SELECT id, document_id, stage, attempts FROM processing_jobs "
            "WHERE stage = ? AND status IN ('pending') AND (next_retry_at IS NULL OR next_retry_at <= ?) "
            "ORDER BY id ASC LIMIT 1",
            (stage, _iso(_now())),
        ).fetchone()
        if not row:
            return None
        connection.execute(
            "UPDATE processing_jobs SET status = 'running', attempts = attempts + 1, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (row["id"],),
        )
        return connection.execute(
            "SELECT id, document_id, stage, attempts FROM processing_jobs WHERE id = ?", (row["id"],)
        ).fetchone()


def mark_done(job_id: int) -> None:
    with transaction() as connection:
        connection.execute(
            "UPDATE processing_jobs SET status = 'done', last_error = NULL, updated_at = CURRENT_TIMESTAMP "
            "WHERE id = ?",
            (job_id,),
        )


def mark_failed(job_id: int, error: str, retry_at: datetime | None = None) -> None:
    """Ghi lỗi. Nếu còn lượt thử thì đưa về hàng đợi với thời điểm thử lại."""
    with transaction() as connection:
        if retry_at is None:
            connection.execute(
                "UPDATE processing_jobs SET status = 'error', last_error = ?, updated_at = CURRENT_TIMESTAMP "
                "WHERE id = ?",
                (error[:500], job_id),
            )
            return
        connection.execute(
            "UPDATE processing_jobs SET status = 'pending', last_error = ?, next_retry_at = ?, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (error[:500], _iso(retry_at), job_id),
        )


def requeue_stale(minutes: int = 10) -> int:
    """Đưa các việc bị kẹt ở trạng thái running (do tắt máy) về hàng đợi lại."""
    threshold = _iso(_now() - timedelta(minutes=minutes))
    with transaction() as connection:
        cursor = connection.execute(
            "UPDATE processing_jobs SET status = 'pending', next_retry_at = NULL, updated_at = CURRENT_TIMESTAMP "
            "WHERE status = 'running' AND updated_at <= ?",
            (threshold,),
        )
        return int(cursor.rowcount or 0)


def stats() -> dict:
    with read_connection() as connection:
        rows = connection.execute(
            "SELECT status, COUNT(*) AS total FROM processing_jobs GROUP BY status"
        ).fetchall()
    return {row["status"]: int(row["total"]) for row in rows}


def list_recent(limit: int = 20) -> list[dict]:
    with read_connection() as connection:
        rows = connection.execute(
            "SELECT id, document_id, stage, status, attempts, last_error, updated_at "
            "FROM processing_jobs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def next_backoff_seconds(attempts: int) -> int:
    """Thời gian chờ trước khi thử lại: 5 giây, 30 giây, 120 giây."""
    return (5, 30, 120)[min(max(attempts, 1), 3) - 1]
