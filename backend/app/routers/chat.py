"""Endpoint trợ lý AI: hỏi đáp có ngữ cảnh tài liệu và kiểm tra tình trạng hệ thống."""

from __future__ import annotations

import logging
import sqlite3

from fastapi import APIRouter, Header, HTTPException, Request, status

from ..config import get_settings
from ..db import read_connection
from ..deps import get_current_user
from ..repositories import citations as citations_repo
from ..repositories import conversations as conversations_repo
from ..repositories import documents as documents_repo
from ..repositories import settings_repo
from ..schemas import ChatRequest, ChatResponse, Citation
from ..services import retrieval
from ..services.embeddings import EmbeddingError, EmbeddingUnavailable
from ..services.llm import (
    NO_CONTEXT_ANSWER,
    RAG_SYSTEM_PROMPT,
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
logger = logging.getLogger("mindora.api.chat")


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


async def _find_context(
    owner_id: int, message: str, document_id: int | None
) -> list[retrieval.RetrievedChunk]:
    """Tìm ngữ cảnh trong tài liệu của người dùng.

    Lỗi sinh vector không được làm sập câu trả lời: ghi nhận vào nhật ký rồi coi như
    không có ngữ cảnh, vì hệ thống vẫn phải trả lời được bằng LLM thuần.
    """
    try:
        return await retrieval.search(owner_id, message, document_id)
    except EmbeddingUnavailable as exc:
        logger.warning("Không sinh được vector cho câu hỏi: %s", exc)
        return []
    except EmbeddingError as exc:
        logger.warning("Lỗi dịch vụ vector nhúng: %s", exc)
        return []


def _save_citations(message_id: int, chunks: list[retrieval.RetrievedChunk]) -> list[Citation]:
    """Lưu nguồn trích dẫn và trả về dạng gửi cho giao diện."""
    if not chunks:
        return []
    citations = [
        Citation(
            document_id=chunk.document_id,
            chunk_id=chunk.chunk_id,
            file_name=chunk.file_name,
            page_number=chunk.page_number,
            snippet=chunk.snippet,
            score=chunk.score,
        )
        for chunk in chunks
    ]
    citations_repo.add_citations(
        message_id,
        [
            (item.document_id, item.chunk_id, item.file_name, item.page_number, item.snippet, item.score)
            for item in citations
        ],
    )
    return citations


def _ready_document_ids(owner_id: int) -> list[int]:
    """Các tài liệu đã xử lý xong của người dùng, tức là có thể truy hồi."""
    return [int(row["id"]) for row in documents_repo.list_by_status("ready", owner_id)]


@router.post("/api/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    request: Request,
    authorization: str | None = Header(default=None),
) -> ChatResponse:
    """Nhận câu hỏi, tìm ngữ cảnh trong tài liệu rồi trả lời kèm nguồn trích dẫn.

    Không có ngữ cảnh thì vẫn trả lời tự do như trợ lý thông thường; chỉ khi người
    dùng chỉ định một tài liệu cụ thể mà tài liệu đó không liên quan thì mới nói
    "chưa đủ thông tin" (NFR-4).
    """
    user = get_current_user(request, authorization)
    message = payload.message.strip()
    owner_id = int(user["id"])

    # Tài liệu được chỉ định phải là của chính người hỏi, nếu không sẽ báo 404.
    if payload.document_id is not None and not documents_repo.get_owned(payload.document_id, owner_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tài liệu."
        )

    try:
        conversation_id = conversations_repo.start_turn(owner_id, message, payload.conversation_id)
    except conversations_repo.ConversationNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cuộc hội thoại."
        ) from exc

    # Tối ưu: chỉ truy hồi tài liệu khi người dùng thực sự đã có tài liệu xử lý xong.
    # Nhờ vậy câu hỏi thông thường không tốn thêm một lượt gọi mô hình nhúng.
    ready_document_ids = _ready_document_ids(owner_id)
    should_retrieve = payload.document_id is not None or bool(ready_document_ids)
    context_chunks = (
        await _find_context(owner_id, message, payload.document_id) if should_retrieve else []
    )
    context = retrieval.build_context(context_chunks)

    # Chỉ nói "chưa đủ thông tin" khi người dùng yêu cầu trả lời từ MỘT tài liệu cụ thể
    # mà tài liệu đó không có phần nào liên quan (NFR-4).
    if payload.document_id is not None and not context:
        conversations_repo.add_message(conversation_id, "assistant", NO_CONTEXT_ANSWER)
        logger.info(
            "Tài liệu %s không có ngữ cảnh liên quan (hội thoại %s).",
            payload.document_id,
            conversation_id,
        )
        return ChatResponse(
            answer=NO_CONTEXT_ANSWER,
            conversation_id=conversation_id,
            model=await resolve_model(),
            used_documents=False,
        )

    model = await resolve_model()
    # Có ngữ cảnh thì trả lời bám tài liệu và kèm trích dẫn; không có thì trả lời tự do.
    system_prompt = RAG_SYSTEM_PROMPT if context else SYSTEM_PROMPT
    user_content = f"NGỮ CẢNH TỪ TÀI LIỆU:\n{context}\n\nCÂU HỎI: {message}" if context else message

    try:
        result = await get_provider().generate(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
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

    message_id = conversations_repo.add_message(conversation_id, "assistant", result.content)
    citations = _save_citations(message_id, context_chunks) if context else []
    return ChatResponse(
        answer=result.content,
        conversation_id=conversation_id,
        model=result.model,
        citations=citations,
        used_documents=bool(context),
    )
