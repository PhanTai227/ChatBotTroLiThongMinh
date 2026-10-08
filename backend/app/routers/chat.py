"""Endpoint trợ lý AI: hỏi đáp đa lượt có ngữ cảnh tài liệu (kèm streaming SSE).

Nâng cấp so với bản cũ:
- Ngữ cảnh hội thoại: các lượt hỏi trước được đưa vào prompt để AI hiểu "cái này",
  "câu trên"... (tiết kiệm token nhờ giới hạn HISTORY_MESSAGE_LIMIT).
- Streaming: POST /api/chat/stream trả lời từng phần qua SSE để giao diện hiển thị
  ngay, giảm cảm giác chờ đợi trên model cục bộ.
- Ghi tiến độ: mỗi câu hỏi được cộng vào progress_stats theo môn của tài liệu trích dẫn.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import AsyncIterator

from fastapi import APIRouter, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from ..config import get_settings
from ..db import read_connection
from ..deps import get_current_user
from ..repositories import citations as citations_repo
from ..repositories import conversations as conversations_repo
from ..repositories import documents as documents_repo
from ..repositories import progress as progress_repo
from ..repositories import settings_repo
from ..schemas import ChatRequest, ChatResponse, Citation
from ..services import retrieval
from ..services.embeddings import EmbeddingError, EmbeddingUnavailable
from ..services.llm import (
    HISTORY_MESSAGE_LIMIT,
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


def _history_messages(conversation_id: int, question: str) -> list[dict[str, str]]:
    """Các lượt hỏi đáp trước đó trong hội thoại, mới nhất nằm cuối.

    `start_turn` đã lưu câu hỏi hiện tại ở cuối danh sách nên nó phải bị loại ra,
    nếu không AI sẽ thấy chính câu hỏi của mình lặp lại.
    """
    rows = conversations_repo.list_messages(conversation_id)
    if rows and str(rows[-1]["role"]) == "user" and str(rows[-1]["content"]) == question:
        rows = rows[:-1]
    history = [{"role": str(row["role"]), "content": str(row["content"])} for row in rows]
    return history[-HISTORY_MESSAGE_LIMIT:]


def _subject_of_chunks(chunks: list[retrieval.RetrievedChunk], document_id: int | None) -> str | None:
    """Môn học gắn với câu hỏi, suy ra từ tài liệu được trích dẫn (dùng cho tiến độ)."""
    if document_id:
        document = documents_repo.get_by_id(document_id)
        if document and document["subject_tag"]:
            return str(document["subject_tag"])
    for chunk in chunks:
        document = documents_repo.get_by_id(chunk.document_id)
        if document and document["subject_tag"]:
            return str(document["subject_tag"])
    return None


def _map_ai_error(exc: LLMError) -> HTTPException:
    """Đổi lỗi dịch vụ AI sang HTTP nhất quán cho client."""
    if isinstance(exc, LLMTimeout):
        return HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI local phản hồi quá lâu. Hãy thử câu ngắn hơn.",
        )
    if isinstance(exc, LLMModelMissing):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không tìm thấy model trên Ollama. Hãy kiểm tra model đã tải.",
        )
    if isinstance(exc, LLMUnavailable):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không kết nối được Ollama. Hãy kiểm tra Ollama và model đã tải.",
        )
    if isinstance(exc, LLMEmptyResponse):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="AI local không trả về nội dung."
        )
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Lỗi dịch vụ AI.")


async def _prepare_turn(
    payload: ChatRequest, owner_id: int
) -> tuple[int, str, list[retrieval.RetrievedChunk]]:
    """Chuẩn bị lượt hỏi: kiểm tra quyền, lưu câu hỏi, tìm ngữ cảnh.

    Trả về (conversation_id, message, context_chunks).
    """
    message = payload.message.strip()
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
    return conversation_id, message, context_chunks


def _build_prompt(
    conversation_id: int, message: str, context: str
) -> list[dict[str, str]]:
    """Ghép prompt: câu dẫn hệ thống + lịch sử hội thoại + câu hỏi (kèm ngữ cảnh)."""
    system_prompt = RAG_SYSTEM_PROMPT if context else SYSTEM_PROMPT
    user_content = (
        f"NGỮ CẢNH TỪ TÀI LIỆU:\n{context}\n\nCÂU HỎI: {message}" if context else message
    )
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    messages.extend(_history_messages(conversation_id, message))
    messages.append({"role": "user", "content": user_content})
    return messages


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
    owner_id = int(user["id"])
    conversation_id, message, context_chunks = await _prepare_turn(payload, owner_id)
    context = retrieval.build_context(context_chunks)

    # Chỉ nói "chưa đủ thông tin" khi người dùng yêu cầu trả lời từ MỘT tài liệu cụ thể
    # mà tài liệu đó không có phần nào liên quan (NFR-4).
    if payload.document_id is not None and not context:
        conversations_repo.add_message(conversation_id, "assistant", NO_CONTEXT_ANSWER)
        progress_repo.record_question(owner_id, _subject_of_chunks([], payload.document_id))
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
    messages = _build_prompt(conversation_id, message, context)

    try:
        result = await get_provider().generate(messages, model)
    except LLMError as exc:
        raise _map_ai_error(exc) from exc

    message_id = conversations_repo.add_message(conversation_id, "assistant", result.content)
    citations = _save_citations(message_id, context_chunks) if context else []
    progress_repo.record_question(owner_id, _subject_of_chunks(context_chunks, payload.document_id))
    return ChatResponse(
        answer=result.content,
        conversation_id=conversation_id,
        model=result.model,
        citations=citations,
        used_documents=bool(context),
    )


def _sse(data: dict) -> str:
    """Đóng gói một sự kiện SSE."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/api/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    request: Request,
    authorization: str | None = Header(default=None),
) -> StreamingResponse:
    """Trả lời câu hỏi theo streaming (SSE): meta -> từng phần text -> citations -> done.

    Sự kiện:
    - {"type":"meta", conversation_id, model, used_documents}
    - {"type":"delta", text} — một phần câu trả lời
    - {"type":"citations", items: [...]} — nguồn trích dẫn
    - {"type":"done"} — kết thúc thành công
    - {"type":"error", detail} — lỗi AI giữa chừng (đã truy vấn xong nên không đổi được HTTP status)
    """
    user = get_current_user(request, authorization)
    owner_id = int(user["id"])
    conversation_id, message, context_chunks = await _prepare_turn(payload, owner_id)
    context = retrieval.build_context(context_chunks)

    if payload.document_id is not None and not context:
        conversations_repo.add_message(conversation_id, "assistant", NO_CONTEXT_ANSWER)
        progress_repo.record_question(owner_id, _subject_of_chunks([], payload.document_id))
        fallback = NO_CONTEXT_ANSWER
        model = await resolve_model()

        async def no_context_stream() -> AsyncIterator[str]:
            yield _sse(
                {
                    "type": "meta",
                    "conversation_id": conversation_id,
                    "model": model,
                    "used_documents": False,
                }
            )
            yield _sse({"type": "delta", "text": fallback})
            yield _sse({"type": "done"})

        return StreamingResponse(
            no_context_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    model = await resolve_model()
    messages = _build_prompt(conversation_id, message, context)
    provider = get_provider()

    async def event_stream() -> AsyncIterator[str]:
        yield _sse(
            {
                "type": "meta",
                "conversation_id": conversation_id,
                "model": model,
                "used_documents": bool(context),
            }
        )
        parts: list[str] = []
        try:
            async for chunk in provider.stream(messages, model):
                parts.append(chunk)
                yield _sse({"type": "delta", "text": chunk})
        except LLMError as exc:
            logger.warning("Streaming gặp lỗi ở hội thoại %s: %s", conversation_id, exc)
            yield _sse({"type": "error", "detail": _map_ai_error(exc).detail})
            return

        answer = "".join(parts).strip()
        if not answer:
            yield _sse({"type": "error", "detail": "AI local không trả về nội dung."})
            return

        message_id = conversations_repo.add_message(conversation_id, "assistant", answer)
        citations = _save_citations(message_id, context_chunks) if context else []
        progress_repo.record_question(owner_id, _subject_of_chunks(context_chunks, payload.document_id))
        yield _sse({"type": "citations", "items": [item.model_dump() for item in citations]})
        yield _sse({"type": "done"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


