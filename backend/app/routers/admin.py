"""Endpoint quản trị: người dùng, cấu hình, thống kê, nhật ký thao tác."""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request, status

from ..deps import get_current_user, require_admin
from ..repositories import audit as audit_repo
from ..repositories import conversations as conversations_repo
from ..repositories import sessions as sessions_repo
from ..repositories import settings_repo
from ..repositories import users as users_repo
from ..schemas import SettingRequest, UserActionRequest
from ..security import hash_password

router = APIRouter(prefix="/api/admin", tags=["Quản trị"])


def _admin(request: Request, authorization: str | None) -> dict:
    admin = get_current_user(request, authorization)
    require_admin(admin)
    return admin


@router.get("/users")
async def admin_users(request: Request, authorization: str | None = Header(default=None)) -> list[dict]:
    _admin(request, authorization)
    return users_repo.list_all()


@router.patch("/users")
async def update_user(
    payload: UserActionRequest,
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict:
    admin = _admin(request, authorization)
    target = users_repo.get_by_id(payload.user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tài khoản.")
    is_self = payload.user_id == int(admin["id"])

    if payload.role is not None:
        if payload.role not in {"user", "admin"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vai trò không hợp lệ.")
        if is_self and payload.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể tự hạ quyền tài khoản đang đăng nhập.",
            )
        users_repo.set_role(payload.user_id, payload.role)
    if payload.is_active is not None:
        if is_self and payload.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể tự khoá tài khoản đang đăng nhập.",
            )
        users_repo.set_active(payload.user_id, payload.is_active)
        if not payload.is_active:
            sessions_repo.delete_sessions_for_user(payload.user_id)
    if payload.new_password:
        users_repo.set_password_hash(payload.user_id, hash_password(payload.new_password))
        sessions_repo.delete_sessions_for_user(payload.user_id)

    audit_repo.log_action(int(admin["id"]), "update_user", payload.user_id)
    return {"message": "Đã cập nhật người dùng"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict:
    admin = _admin(request, authorization)
    if user_id == int(admin["id"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể xoá tài khoản đang đăng nhập.",
        )
    if not users_repo.get_by_id(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tài khoản.")
    target_email = str(users_repo.get_by_id(user_id)["email"])
    users_repo.delete_user(user_id)
    # Tài khoản đã bị xoá nên nhật ký chỉ lưu thông tin mô tả, không giữ khoá ngoại.
    audit_repo.log_action(
        int(admin["id"]), "delete_user", None, detail=f"user_id={user_id}, email={target_email}"
    )
    return {"message": "Đã xoá người dùng"}


@router.get("/settings")
async def admin_settings(request: Request, authorization: str | None = Header(default=None)) -> list[dict]:
    _admin(request, authorization)
    return settings_repo.list_all()


@router.patch("/settings/{setting_key}")
async def update_setting(
    setting_key: str,
    payload: SettingRequest,
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict:
    admin = _admin(request, authorization)
    if setting_key not in settings_repo.ALLOWED_KEYS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cấu hình.")
    settings_repo.set_value(setting_key, payload.value)
    audit_repo.log_action(int(admin["id"]), "update_setting")
    from ..services.llm import invalidate_caches

    invalidate_caches()
    return {"message": "Đã cập nhật cấu hình"}


@router.get("/stats")
async def admin_stats(request: Request, authorization: str | None = Header(default=None)) -> dict:
    _admin(request, authorization)
    return {
        "users": users_repo.count_all(),
        "active_users": users_repo.count_active(),
        "conversations": conversations_repo.count_all(),
        "questions": conversations_repo.count_user_messages(),
    }
