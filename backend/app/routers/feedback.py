"""Endpoint phản hồi: học viên gửi đánh giá, quản trị viên trả lời (FR mới)."""

from __future__ import annotations

from fastapi import APIRouter, Header, Request, status

from ..deps import get_current_user
from ..repositories import feedback as feedback_repo
from ..schemas import FeedbackCreate

router = APIRouter(prefix="/api/feedback", tags=["Phản hồi"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_feedback(
    payload: FeedbackCreate,
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict:
    user = get_current_user(request, authorization)
    return feedback_repo.create(int(user["id"]), payload.rating, payload.category, payload.content)


@router.get("")
async def my_feedback(request: Request, authorization: str | None = Header(default=None)) -> dict:
    user = get_current_user(request, authorization)
    return {"items": feedback_repo.list_for_user(int(user["id"]))}
