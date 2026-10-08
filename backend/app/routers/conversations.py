"""Endpoint hội thoại: xem danh sách, đọc tin nhắn và xoá (FR-B6, FR-C5)."""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request, status

from ..deps import get_current_user
from ..repositories import conversations as conversations_repo

router = APIRouter(prefix="/api/conversations", tags=["Hội thoại"])


@router.get("")
async def list_conversations(request: Request, authorization: str | None = Header(default=None)) -> dict:
    user = get_current_user(request, authorization)
    return {"items": conversations_repo.list_for_user(int(user["id"]))}


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: int, request: Request, authorization: str | None = Header(default=None)
) -> dict:
    user = get_current_user(request, authorization)
    row = conversations_repo.get_conversation(conversation_id)
    # Hội thoại cũ có thể chưa gán chủ (user_id NULL): cho phép đọc như is_accessible.
    if not row or (row["user_id"] is not None and int(row["user_id"]) != int(user["id"])):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy hội thoại."
        )
    return {**dict(row), "messages": conversations_repo.list_messages(conversation_id)}


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int, request: Request, authorization: str | None = Header(default=None)
) -> dict:
    user = get_current_user(request, authorization)
    if not conversations_repo.delete_conversation(conversation_id, int(user["id"])):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy hội thoại."
        )
    return {"message": "Đã xoá hội thoại"}
