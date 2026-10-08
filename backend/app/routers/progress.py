"""Endpoint tiến độ học tập: thống kê, hoạt động theo ngày và gợi ý (Module F)."""

from __future__ import annotations

from fastapi import APIRouter, Header, Request

from ..deps import get_current_user
from ..repositories import progress as progress_repo

router = APIRouter(prefix="/api/progress", tags=["Tiến độ"])


@router.get("")
async def get_progress(request: Request, authorization: str | None = Header(default=None)) -> dict:
    user = get_current_user(request, authorization)
    user_id = int(user["id"])

    return {
        "overview": progress_repo.overview(user_id),
        "subjects": progress_repo.subjects(user_id),
        "suggestion": progress_repo.suggestion(user_id),
        "daily_activity": [
            {"day": day, **counts}
            for day, counts in progress_repo.daily_activity(user_id).items()
        ],
        "activities": progress_repo.recent_activities(user_id),
    }
