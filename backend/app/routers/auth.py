"""Endpoint xác thực: đăng ký, đăng nhập, đăng xuất, thông tin người dùng."""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request, status

from ..config import get_settings
from ..deps import get_current_user
from ..repositories import sessions as sessions_repo
from ..repositories import users as users_repo
from ..schemas import AuthRequest, LoginRequest
from ..security import hash_password, new_session_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["Xác thực"])


def _public_user(row) -> dict:
    return {
        "id": int(row["id"]),
        "full_name": row["full_name"],
        "email": row["email"],
        "role": row["role"],
    }


def _issue_session(user_id: int) -> str:
    token = new_session_token()
    sessions_repo.create_session(user_id, token, get_settings().session_days)
    return token


@router.post("/register")
async def register(payload: AuthRequest) -> dict:
    email = payload.email.strip().lower()
    full_name = payload.full_name.strip()
    try:
        user_id = users_repo.create_user(full_name, email, hash_password(payload.password))
    except users_repo.EmailAlreadyExists as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email đã được sử dụng.") from exc
    return {
        "token": _issue_session(user_id),
        "user": {"id": user_id, "full_name": full_name, "email": email, "role": "user"},
    }


@router.post("/login")
async def login(payload: LoginRequest) -> dict:
    user = users_repo.get_by_email(payload.email.strip().lower())
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Email hoặc mật khẩu không đúng."
        )
    if not user["is_active"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị khoá.")
    users_repo.touch_last_login(int(user["id"]))
    return {"token": _issue_session(int(user["id"])), "user": _public_user(user)}


@router.get("/me")
async def me(request: Request, authorization: str | None = Header(default=None)) -> dict:
    return {"user": get_current_user(request, authorization)}


@router.post("/logout")
async def logout(request: Request, authorization: str | None = Header(default=None)) -> dict:
    get_current_user(request, authorization)
    from ..deps import extract_token

    token = extract_token(authorization)
    if token:
        sessions_repo.delete_session(token)
    return {"message": "Đã đăng xuất"}
