"""Endpoint trợ lý AI: hỏi đáp và kiểm tra tình trạng hệ thống."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Header, HTTPException, Request, status

from ..config import get_settings
from ..db import read_connection
from ..deps import get_current_user
from ..repositories import conversations as conversations_repo
from ..repositories import settings_repo
from ..schemas import ChatRequest, ChatResponse
from ..services.llm import (
    SYSTEM_PROMPT,
    LLMEmptyResponse,
    LLMError,
    LLMModelMissing,
    LLMTimeout,
    LLMUnavailable,
    get_provider,
    resolve_model,
)

router = APIRouter(tags=["Trợ lý AI"])


@router.get("/api/health")
async def health() -> dict:
    """Báo trạng thái cơ sở dữ liệu và dịch vụ AI, không yêu cầu đăng nhập."""
    settings = get_settings()
    database = "ok"
    try:
        with read_connection() as connection:
            connection.execute("SELECT 1").fetchone()
    except sqlite3.Error:
        database = "error"

    provider = get_provider()
    ollama_state = "unavailable"
    models: list[str] = []
    version: str | None = None
    try:
        models = await provider.list_models()
        ollama_state = "connected"
        version = await provider.version()
    except LLMError:
        ollama_state = "unavailable"

    model = settings_repo.get_value("ai_model", settings.ollama_model) or settings.ollama_model
    model_available = ollama_state == "connected" and any(
        name == model or name.startswith(model) for name in models
    )

    issues: list[str] = []
    if database != "ok":
        issues.append("database_unavailable")
    if ollama_state != "connected":
        issues.append("ai_unreachable")
    elif not models:
        issues.append("no_model_installed")
    elif not model_available:
        issues.append("configured_model_missing")

    return {
        "status": "ok" if not issues else "degraded",
        "ollama": ollama_state,
        "ollama_version": version,
        "ollama_models": models,
        "model": model,
        "model_available": model_available,
        "database": database,
        "llm_provider": settings.llm_provider,
        "app_mode": settings.app_mode,
        "issues": issues,
    }


@router.post("/api/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    request: Request,
    authorization: str | None = Header(default=None),
) -> ChatResponse:
    """Nhận câu hỏi, lưu vào lịch sử, gửi tới AI cục bộ rồi lưu câu trả lời."""
    user = get_current_user(request, authorization)
    message = payload.message.strip()

    try:
        conversation_id = conversations_repo.start_turn(int(user["id"]), message, payload.conversation_id)
    except conversations_repo.ConversationNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cuộc hội thoại."
        ) from exc

    model = await resolve_model()
    try:
        result = await get_provider().generate(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
            model,
        )
    except LLMTimeout as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI local phản hồi quá lâu. Hãy thử câu ngắn hơn.",
        ) from exc
    except LLMModelMissing as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Không tìm thấy model {model} trên Ollama. Hãy kiểm tra model đã tải.",
        ) from exc
    except LLMUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không kết nối được Ollama. Hãy kiểm tra Ollama và model đã tải.",
        ) from exc
    except LLMEmptyResponse as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="AI local không trả về nội dung."
        ) from exc

    conversations_repo.add_message(conversation_id, "assistant", result.content)
    return ChatResponse(answer=result.content, conversation_id=conversation_id, model=result.model)
