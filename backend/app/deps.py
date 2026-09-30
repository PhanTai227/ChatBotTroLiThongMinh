"""Xác thực và phân quyền dùng chung cho các router."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Header, HTTPException, Request, status

from .repositories import sessions as sessions_repo

BEARER_PREFIX = "Bearer "


def extract_token(authorization: str | None) -> str | None:
    """Lấy token từ header Authorization, trả về None nếu không hợp lệ."""
    if not authorization or not authorization.startswith(BEARER_PREFIX):
        return None
    return authorization.removeprefix(BEARER_PREFIX).strip()


def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict:
    """Lấy người dùng hiện tại từ token phiên; ném 401 nếu thiếu hoặc hết hạn."""
    token = extract_token(authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bạn cần đăng nhập.")
    row = sessions_repo.find_user_by_token(token)
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên đăng nhập đã hết hạn.")
    if not row["is_active"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị khoá.")
    user = dict(row)
    request.state.user_id = user["id"]
    return user


def require_admin(user: dict) -> None:
    if user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chỉ quản trị viên được phép thực hiện.")


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()
