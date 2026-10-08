"""Truy vấn tiến độ học tập: thống kê, hoạt động theo ngày, gợi ý (Module F).

Tiến độ được ghi theo số câu hỏi học viên đặt cho từng môn, không liên quan quiz.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from ..db import read_connection, transaction

DEFAULT_SUBJECT = "Chung"


def record_question(user_id: int, subject: str | None) -> None:
    """Ghi +1 câu hỏi cho môn học sau khi trợ lý trả lời xong."""
    subject = (subject or "").strip() or DEFAULT_SUBJECT
    with transaction() as connection:
        connection.execute(
            """INSERT INTO progress_stats(user_id, subject_tag, questions_asked)
               VALUES (?, ?, 1)
               ON CONFLICT(user_id, subject_tag)
               DO UPDATE SET questions_asked = questions_asked + 1, updated_at = CURRENT_TIMESTAMP""",
            (user_id, subject),
        )


def overview(user_id: int) -> dict:
    """Tổng quan cho dashboard: tài liệu, câu hỏi, hội thoại."""
    with read_connection() as connection:
        documents = connection.execute(
            "SELECT COUNT(*) FROM documents WHERE owner_id = ?", (user_id,)
        ).fetchone()[0]
        questions = connection.execute(
            """SELECT COUNT(*) FROM messages m
               JOIN conversations c ON c.id = m.conversation_id
               WHERE c.user_id = ? AND m.role = 'user'""",
            (user_id,),
        ).fetchone()[0]
        conversations = connection.execute(
            "SELECT COUNT(*) FROM conversations WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
    return {
        "documents": int(documents),
        "questions": int(questions),
        "conversations": int(conversations),
    }


def subjects(user_id: int) -> list[dict]:
    """Tiến độ theo từng môn học, xếp giảm dần theo số câu hỏi đã đặt."""
    with read_connection() as connection:
        rows = connection.execute(
            """SELECT subject_tag AS subject, study_minutes, questions_asked
               FROM progress_stats WHERE user_id = ?
               ORDER BY questions_asked DESC, subject_tag""",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def suggestion(user_id: int) -> dict | None:
    """Môn có tài liệu sẵn sàng nhưng học viên chưa đặt câu hỏi nào."""
    with read_connection() as connection:
        row = connection.execute(
            """SELECT d.subject_tag AS subject
               FROM documents d
               LEFT JOIN progress_stats p
                      ON p.user_id = d.owner_id AND p.subject_tag = d.subject_tag
               WHERE d.owner_id = ? AND d.status = 'ready'
                 AND d.subject_tag IS NOT NULL AND length(trim(d.subject_tag)) > 0
                 AND IFNULL(p.questions_asked, 0) = 0
               ORDER BY d.created_at DESC
               LIMIT 1""",
            (user_id,),
        ).fetchone()
    if not row:
        return None
    subject = str(row["subject"])
    return {
        "subject": subject,
        "reason": (
            f"Bạn đã có tài liệu môn {subject} nhưng chưa hỏi câu hỏi nào. "
            "Hãy thử đặt câu hỏi để kiểm tra độ hiểu bài."
        ),
    }


def daily_activity(user_id: int, days: int = 84) -> dict[str, dict]:
    """Số câu hỏi và tài liệu theo từng ngày (dùng cho biểu đồ và lịch học 12 tuần)."""
    since = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%d")
    activity: dict[str, dict] = {}

    def bucket(day: str) -> dict:
        return activity.setdefault(day, {"questions": 0, "documents": 0})

    with read_connection() as connection:
        for row in connection.execute(
            """SELECT date(m.created_at) AS day, COUNT(*) AS total FROM messages m
               JOIN conversations c ON c.id = m.conversation_id
               WHERE c.user_id = ? AND m.role = 'user' AND m.created_at >= ?
               GROUP BY day""",
            (user_id, since),
        ):
            bucket(str(row["day"]))["questions"] = int(row["total"])
        for row in connection.execute(
            """SELECT date(created_at) AS day, COUNT(*) AS total FROM documents
               WHERE owner_id = ? AND created_at >= ? GROUP BY day""",
            (user_id, since),
        ):
            bucket(str(row["day"]))["documents"] = int(row["total"])
    return dict(sorted(activity.items()))


def recent_activities(user_id: int, limit: int = 30) -> list[dict]:
    """Nguồn gộp cho trang Lịch sử: hỏi đáp và tài liệu, sắp xếp mới nhất trước."""
    items: list[dict] = []
    with read_connection() as connection:
        for row in connection.execute(
            """SELECT id, title, created_at FROM conversations
               WHERE user_id = ? ORDER BY id DESC LIMIT ?""",
            (user_id, limit),
        ):
            items.append(
                {
                    "id": f"chat-{row['id']}",
                    "type": "Chat AI",
                    "title": row["title"],
                    "detail": "Câu hỏi với trợ lý AI",
                    "subject": None,
                    "at": row["created_at"],
                }
            )
        for row in connection.execute(
            """SELECT id, file_name, subject_tag, status, created_at FROM documents
               WHERE owner_id = ? ORDER BY id DESC LIMIT ?""",
            (user_id, limit),
        ):
            items.append(
                {
                    "id": f"doc-{row['id']}",
                    "type": "Tài liệu",
                    "title": f"Đã tải lên {row['file_name']}",
                    "detail": "Sẵn sàng cho hỏi đáp"
                    if row["status"] == "ready"
                    else f"Trạng thái: {row['status']}",
                    "subject": row["subject_tag"],
                    "at": row["created_at"],
                }
            )
    items.sort(key=lambda item: item["at"] or "", reverse=True)
    return items[:limit]
