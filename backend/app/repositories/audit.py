"""Ghi nhật ký thao tác quản trị vào bảng audit_logs.

Nguyên tắc: nhật ký không được làm hỏng luồng nghiệp vụ. Nếu ghi nhật ký lỗi
thì chỉ ghi cảnh báo, không ném lỗi ra ngoài.
"""

from __future__ import annotations

import logging

from ..db import transaction

logger = logging.getLogger("mindora.audit")


def log_action(
    admin_id: int | None,
    action: str,
    target_user_id: int | None = None,
    detail: str | None = None,
) -> None:
    try:
        with transaction() as connection:
            connection.execute(
                "INSERT INTO audit_logs(admin_id, action, target_user_id, detail) VALUES (?, ?, ?, ?)",
                (admin_id, action, target_user_id, detail),
            )
    except Exception:  # noqa: BLE001 - nhật ký không được chặn luồng nghiệp vụ
        logger.exception("Không ghi được nhật ký cho thao tác %s", action)
